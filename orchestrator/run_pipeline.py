import argparse
import sys
import json
import logging
from typing import List, Any

from validators.validate import validate
from orchestrator.rag_retriever import ContextRetriever
from prompts.chain import AnalysisPromptChain
from publishers.mcp_publisher import McpPublisher
from pydantic import ValidationError

def read_input(input_path: str = None) -> str:
    if input_path:
        with open(input_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return sys.stdin.read()

def setup_logging(debug: bool):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s %(levelname)s %(name)s %(message)s')

def parse_args():
    parser = argparse.ArgumentParser(description='Run the analysis pipeline to generate and publish tasks.')
    parser.add_argument('-i', '--input-file', help='Path to the file containing raw requirement. Omit to read from stdin.')
    parser.add_argument('-t', '--topic', default='tasks.analysis', help='Publication topic name.')
    parser.add_argument('--pinecone-index', default=None, help='Name of the Pinecone index to use for RAG.')
    parser.add_argument('--pinecone-environment', default=None, help='Pinecone environment name.')
    parser.add_argument('--pinecone-api-key', default=None, help='Pinecone API key.')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging.')
    return parser.parse_args()

def main():
    args = parse_args()
    setup_logging(args.debug)
    logger = logging.getLogger('run_pipeline')

    try:
        raw_requirement = read_input(args.input_file)
        if not raw_requirement.strip():
            logger.error('No input requirement provided.')
            sys.exit(1)

        # Initialize RAG context retriever
        retriever = ContextRetriever(
            index_name=args.pinecone_index,
            environment=args.pinecone_environment,
            api_key=args.pinecone_api_key
        )
        logger.debug('Querying RAG context for requirement...')
        try:
            context_docs = retriever.query(raw_requirement)
        except Exception as e:
            logger.error('Failed to retrieve context: %s', e)
            sys.exit(1)

        # Initialize the prompt chain
        chain = AnalysisPromptChain()
        logger.info('Extracting intent from requirement...')
        intent = chain.extract_intent(raw_requirement, context_docs)
        logger.debug('Intent extracted: %s', intent)

        logger.info('Decomposing intent into raw tasks...')
        raw_tasks = chain.decompose(intent)
        if not isinstance(raw_tasks, list) or not raw_tasks:
            logger.error('Decomposition returned no tasks.')
            sys.exit(1)

        # Validate tasks
        validated_tasks = []
        for idx, rt in enumerate(raw_tasks):
            try:
                task_model = validate('task', rt)
                validated_tasks.append(task_model)
                logger.debug('Task %d validated: %s', idx, task_model)
            except ValidationError as ve:
                logger.error('Validation failed for task %d: %s', idx, ve)
            except Exception as e:
                logger.error('Unexpected error validating task %d: %s', idx, e)

        if not validated_tasks:
            logger.error('No valid tasks to publish.')
            sys.exit(1)

        # Publish tasks
        publisher = McpPublisher(topic=args.topic)
        publish_results = []
        for task in validated_tasks:
            try:
                res = publisher.publish(task)
                publish_results.append({'id': getattr(task, 'id', None), 'result': res})
                logger.info('Published task %s', getattr(task, 'id', None))
            except Exception as e:
                logger.error('Failed to publish task %s: %s', getattr(task, 'id', None), e)

        # Output summary
        summary = {
            'input': args.input_file or 'stdin',
            'intent': intent.dict() if hasattr(intent, 'dict') else intent,
            'validated_tasks': [t.dict() for t in validated_tasks],
            'publish_results': publish_results
        }
        json.dump(summary, sys.stdout, indent=2, default=str)
        sys.stdout.write('\n')
    except Exception as e:
        logging.getLogger('run_pipeline').exception('Pipeline execution failed: %s', e)
        sys.exit(1)

if __name__ == '__main__':
    main()