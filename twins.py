import itertools

from lib.meccg.jsonl import read_jsonl

if __name__ == '__main__':
    characters = list(itertools.chain(
        read_jsonl('var/jsonl/wizards.jsonl'),
        read_jsonl('var/jsonl/wizcharacters.jsonl'),
        read_jsonl('var/jsonl/dracharacters.jsonl'),
        read_jsonl('var/jsonl/dmcharacters.jsonl'),
        read_jsonl('var/jsonl/dmminions.jsonl'),
        read_jsonl('var/jsonl/leringwraith.jsonl'),
        read_jsonl('var/jsonl/leminions.jsonl'),
        read_jsonl('var/jsonl/atsminions.jsonl'),
        read_jsonl('var/jsonl/whwiz.jsonl'),
        read_jsonl('var/jsonl/whchar.jsonl'),
        read_jsonl('var/jsonl/balcharacters.jsonl'),
    ))

    def create_summary(character):
        return ' '.join([
                f"M/I: {character['MIND']}/{character['INFLUENCE']}",
                f"{'/'.join(character['SKILLS'])}",
                f"P/B: {character['PROWESS']}/{character['BODY']}",
            ])

    characters_by_summary = {
        summary: [character for character in characters if create_summary(character) == summary]
        for summary in set(
            create_summary(character)
            for character in characters
        )
    }

    for summary, characters in characters_by_summary.items():
        if len(characters) > 1:
            print(summary)
            for character in characters:
                print(character['NAME'])
            print()
