'''Parse yaml files while supporting updates (newer files modify previous definitions)'''

import yaml
from functools import reduce
from pathlib import Path
from typing import List, Dict, Any

def merge_item(x, y):
    if y is None:
        ret = x
    elif x is None:
        ret = y
    else:
        if type(x) != type(y):
            ret = y
        elif isinstance(x, dict):
            keys = set(x.keys()).union(set(y.keys()))
            new_dict = {}
            for k in keys:
                if k in x and k in y:
                    new_dict[k] = merge_item(x[k], y[k])
                elif k in x:
                    new_dict[k] = x[k]
                elif k in y:
                    new_dict[k] = y[k]
                else:
                    raise RuntimeError(f'Key {k} not in x or y, this should never happen!')
            ret = new_dict
        elif isinstance(x, list):
            ret = x + y
        else:   # y dominates
            ret = y
    return ret


def merge_content(content: List[Dict[str, Any]]) -> Dict[str, Any]:
    '''Merge content'''
    return reduce(merge_item, content)


def parse_merge_yaml(_yamls: List[str]) -> Dict[str, Any]:
    return merge_content([yaml.safe_load(_yaml) for _yaml in _yamls])


def parse_merge_files(files: List[Path]) -> Dict[str, Any]:
    content = []
    return parse_merge_yaml([f.open("r").read() for f in files])

def parse_concat_merge_files(concats: List[Path], merge: List[Path]) -> Dict[str, Any]:
    return parse_merge_yaml([
        '\n'.join([f.open("r").read() for f in concats]),
        *[f.open("r").read() for f in merge],
    ])


if __name__ == "__main__":
    data1 = """
metadata:

  company: super cool

  authors:
    created:
      name: bob ross
      date: 2023-03-29
    reviewed:
      name: n/a
      date: n/a

notes:
  - some note 1
  - some note 2
  - some note 3
    """

    data2 = """
notes:
  - more note 4
  - more note 5
    """

    data3 = """
metadata:
    pn: test-02
    authors:
        created:
          date: 2023-04-10
        reviewed:
          name: Pablo Picasso
          date: 2023-04-11

notes:
  - even more note 6
  - so much note 7
    """

    expected = {
        'metadata': {
            'company': 'super cool',
            'pn': 'test-02',
            'authors': {
                'created': {
                    'name': 'bob ross',
                    'date': '2023-04-10',
                },
                'reviewed': {
                    'name': 'Pablo Picasso',
                    'date': '2023-04-11',
                },
            },
        },
        'notes': [
            'some note 1',
            'some note 2',
            'some note 3',
            'more note 4',
            'more note 5',
            'even more note 6',
            'so much note 7',
        ]
    }
    parsed = parse_merge_yaml([data1, data2, data3])
    symmetric_diff = set(parsed) ^ set(expected)
    if symmetric_diff:
        print(symmetric_diff)
        raise ValueError()
