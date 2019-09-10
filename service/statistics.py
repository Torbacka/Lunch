from service.client.mongo_client import get_all_votes


def statistics():
    votes = get_all_votes()
    winning_votes = dict()
    temp = dict()
    for suggestions in votes:
        for key in suggestions.keys():
            suggestion = suggestions[key]
            if temp.get('size') is None:
                temp['size'] = len(suggestion['vote'])
                temp['array'] = suggestion['vote']
            elif temp.get('size') < len(suggestion['vote']):
                temp['size'] = len(suggestion['vote'])
                temp['array'] = suggestion['vote']
        print(temp)


if __name__ == '__main__':
    statistics()
