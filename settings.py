import os

CHAT_SERVICE_PORT = 2929

PATH_TO_INTER = '/usr/local/bin/python3'

CUR_DIR = os.path.dirname(__file__)
PATH_TO_SCRIPT = os.path.join(CUR_DIR, 'pp.py')

INTER_ENVS = {'PYTHONIOENCODING': 'utf8', 'PYTHONUNBUFFERED': '0'}

TEST_CONNECTION_ID = 'o000122124ewr'
TEST_PREFIX = 'req'

TEST_COMMAND_PIPELINE = [
    ({
        'do': 'run',
        'code': '''
print('So')
def checkio(data):
    return data ** 2
        '''
    }, {'do': 'done', 'result': None}),
    ({
        'do': 'exec',
        'func': 'checkio',
        'in': 20
    }, None)
]


# TEST_COMMAND_PIPELINE = [
#     ({
#         'do': 'run',
#         'code': '''
# def checkio(data)
#     return data ** 2
#         '''
#     }, {'do': 'run_fail'})
# ]