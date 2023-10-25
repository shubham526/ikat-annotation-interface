import json
import random
import os
import argparse
import sys
import gzip
import hashlib
from tqdm import tqdm


def load_topics(topics_file):
    # Load the topic file
    with open(topics_file, 'r') as f:
        return json.load(f)


def load_turns_file(turns_file):
    # Load turn ids from the turn id file
    with open(turns_file, 'r', encoding='utf-8-sig') as f:
        lines = [line.strip() for line in f.readlines()]
        turns = [line.split(':')[0].strip() for line in lines]
        return [item for item in turns if item]


def create_data(run_directory, turn_ids, topics):
    results = []

    # Extract data for each turn_id
    for turn_id in tqdm(turn_ids, total=len(turn_ids)):
        # turn_id = '14-2_6'
        topic_subtree, turn = turn_id.split('_')
        topic_id, subtree_id = topic_subtree.split('-')

        # Find the corresponding conversation
        for topic in topics:
            t_id = topic['number'].split('-')[0]
            s_id = topic['number'].split('-')[1]
            if int(t_id) == int(topic_id) and int(s_id) == int(subtree_id):
                for t in topic['turns']:
                    if t['turn_id'] == int(turn):
                        # Extract conversation context
                        idx = topic['turns'].index(t)
                        first_utterance = "USER: " + topic['turns'][0]['resolved_utterance']
                        previous_turns = topic['turns'][max(0, idx - 3):idx]
                        context_parts = [first_utterance]

                        for ct in previous_turns:
                            context_parts.append("USER: " + ct['utterance'])
                            context_parts.append("SYSTEM: " + ct['response'])

                        # Add the current turn's utterance
                        context_parts.append("USER: " + t['utterance'])

                        context = '\n'.join(context_parts)

                        # Extract response from each run file in the directory
                        for run_file in os.listdir(run_directory):
                            if run_file.endswith('.gz'):
                                with gzip.open(os.path.join(run_directory, run_file), 'rt') as f:
                                    run = json.load(f)
                                    for r in run['turns']:
                                        if r['turn_id'] == turn_id:
                                            # Check each response for a passage marked true
                                            for resp in r['responses']:
                                                if any(passage.get('used', False) for passage in
                                                       resp['passage_provenance']):
                                                    response = resp['text']

                                                    conversation_id = turn_id.rsplit('_', 1)[0]
                                                    hashed_conversation_id = hashlib.md5(
                                                        conversation_id.encode()).hexdigest()

                                                    # Create the JSON object
                                                    results.append({
                                                        'conversation_id': hashed_conversation_id,
                                                        'conversation_context': context,
                                                        'turn_id': turn_id,
                                                        'run_id': run['run_name'],
                                                        'response': f'SYSTEM: {response}'
                                                    })
                                                    break

                break

    # Shuffle and batch the results
    random.shuffle(results)
    batches = [results[i:i + 20] for i in range(0, len(results), 20)]
    return batches


def write_to_file(data, save):
    # Save the batches to JSON files
    for idx, batch in enumerate(data):
        save_path = os.path.join(save, f'batch_{idx + 1}.json')
        with open(save_path, 'w') as f:
            json.dump(batch, f, indent=4)


def main():
    parser = argparse.ArgumentParser("Create the data for iKAT response evaluation.")
    parser.add_argument("--turns", help='Path to the file containing turns to judge.', required=True)
    parser.add_argument("--topics", help='Path to the topics file.', required=True)
    parser.add_argument("--runs", help='Directory containing run files to evaluate.', required=True)
    parser.add_argument("--save", help='Directory where data will be saved.', required=True)
    args = parser.parse_args(args=None if sys.argv[1:] else ['--help'])

    print('Loading turns...')
    turns = load_turns_file(turns_file=args.turns)
    print('[Done].')

    print('Loading topics...')
    topics = load_topics(topics_file=args.topics)
    print('[Done].')

    print('Creating data...')
    data = create_data(run_directory=args.runs, topics=topics, turn_ids=turns)
    print('[Done].')

    print('Saving to file...')
    write_to_file(data=data, save=args.save)
    print('[Done].')
    print('Data saved to ==> {}'.format(args.save))


if __name__ == '__main__':
    main()
