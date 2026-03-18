from loguru import logger
from pyzotero import zotero
from omegaconf import DictConfig
from .utils import glob_match
from .retriever import get_retriever_cls
from .protocol import CorpusPaper
import random
from datetime import datetime
from .reranker import get_reranker_cls
from .construct_email import render_email
from .utils import send_email
from openai import OpenAI
from tqdm import tqdm

class Executor:
    def __init__(self, config:DictConfig):
        self.config = config
        self.retrievers = {
            source: get_retriever_cls(source)(config) for source in config.executor.source
        }
        self.reranker = get_reranker_cls(config.executor.reranker)(config)

        # Create a separate fast reranker for first stage if pre-filtering is enabled
        pre_filter_num = config.executor.get('pre_filter_num', None)
        if pre_filter_num:
            first_stage_reranker = config.executor.get('first_stage_reranker', 'llm_fast')
            logger.info(f"Two-stage filtering enabled: using {first_stage_reranker} for first stage")
            self.first_stage_reranker = get_reranker_cls(first_stage_reranker)(config)
        else:
            self.first_stage_reranker = None

        self.openai_client = OpenAI(api_key=config.llm.api.key, base_url=config.llm.api.base_url)
    def fetch_zotero_corpus(self) -> list[CorpusPaper]:
        logger.info("Fetching zotero corpus")
        zot = zotero.Zotero(self.config.zotero.user_id, 'user', self.config.zotero.api_key)
        collections = zot.everything(zot.collections())
        collections = {c['key']:c for c in collections}
        corpus = zot.everything(zot.items(itemType='conferencePaper || journalArticle || preprint'))
        corpus = [c for c in corpus if c['data']['abstractNote'] != '']
        def get_collection_path(col_key:str) -> str:
            if p := collections[col_key]['data']['parentCollection']:
                return get_collection_path(p) + '/' + collections[col_key]['data']['name']
            else:
                return collections[col_key]['data']['name']
        for c in corpus:
            paths = [get_collection_path(col) for col in c['data']['collections']]
            c['paths'] = paths
            # Extract tags
            tags = [tag['tag'] for tag in c['data'].get('tags', [])]
            c['tags'] = tags
        logger.info(f"Fetched {len(corpus)} zotero papers")
        return [CorpusPaper(
            title=c['data']['title'],
            abstract=c['data']['abstractNote'],
            added_date=datetime.strptime(c['data']['dateAdded'], '%Y-%m-%dT%H:%M:%SZ'),
            paths=c['paths'],
            tags=c['tags']
        ) for c in corpus]
    
    def filter_corpus(self, corpus:list[CorpusPaper]) -> list[CorpusPaper]:
        if not self.config.zotero.include_path:
            return corpus
        new_corpus = []
        logger.info(f"Selecting zotero papers matching include_path: {self.config.zotero.include_path}")
        for c in corpus:
            match_results = [glob_match(p, self.config.zotero.include_path) for p in c.paths]
            if any(match_results):
                new_corpus.append(c)
        samples = random.sample(new_corpus, min(5, len(new_corpus)))
        samples = '\n'.join([c.title + ' - ' + '\n'.join(c.paths) for c in samples])
        logger.info(f"Selected {len(new_corpus)} zotero papers:\n{samples}\n...")
        return new_corpus

    
    def run(self):
        corpus = self.fetch_zotero_corpus()
        corpus = self.filter_corpus(corpus)
        if len(corpus) == 0:
            logger.error(f"No zotero papers found. Please check your zotero settings:\n{self.config.zotero}")
            return
        all_papers = []
        for source, retriever in self.retrievers.items():
            logger.info(f"Retrieving {source} papers...")
            papers = retriever.retrieve_papers()
            if len(papers) == 0:
                logger.info(f"No {source} papers found")
                continue
            logger.info(f"Retrieved {len(papers)} {source} papers")
            all_papers.extend(papers)
        logger.info(f"Total {len(all_papers)} papers retrieved from all sources")
        reranked_papers = []
        if len(all_papers) > 0:
            # Two-stage filtering if pre_filter_num is set
            pre_filter_num = self.config.executor.get('pre_filter_num', None)

            if pre_filter_num and len(all_papers) > pre_filter_num and self.first_stage_reranker:
                logger.info(f"Stage 1: Fast LLM reranking {len(all_papers)} papers (abstract only)...")
                reranked_papers = self.first_stage_reranker.rerank(all_papers, corpus)
                top_candidates = reranked_papers[:pre_filter_num]
                logger.info(f"Stage 1: Selected top {len(top_candidates)} candidates")

                # Now extract PDF for top candidates only
                logger.info(f"Stage 2: Extracting PDF for top {len(top_candidates)} candidates...")
                for paper in tqdm(top_candidates, desc="Extracting PDFs"):
                    # Re-extract with PDF if it was skipped
                    if paper.full_text is None and paper.source in self.retrievers:
                        retriever = self.retrievers[paper.source]
                        if hasattr(retriever, 'extract_full_text'):
                            try:
                                paper.full_text = retriever.extract_full_text(paper)
                            except Exception as e:
                                logger.warning(f"Failed to extract PDF for {paper.title}: {e}")

                # Re-rank with full text using the main reranker
                logger.info("Stage 2: Re-ranking with full text...")
                reranked_papers = self.reranker.rerank(top_candidates, corpus)
            else:
                logger.info("Reranking papers...")
                reranked_papers = self.reranker.rerank(all_papers, corpus)

            # Get top papers for TLDR generation
            max_paper_num = self.config.executor.max_paper_num
            top_papers = reranked_papers[:max_paper_num]

            logger.info(f"Generating TLDR and affiliations for top {len(top_papers)} papers...")
            for p in tqdm(top_papers):
                p.generate_tldr(self.openai_client, self.config.llm)
                p.generate_affiliations(self.openai_client, self.config.llm)

            reranked_papers = top_papers
        elif not self.config.executor.send_empty:
            logger.info("No new papers found. No email will be sent.")
            return
        logger.info("Sending email...")
        email_content = render_email(reranked_papers)
        send_email(self.config, email_content)
        logger.info("Email sent successfully")