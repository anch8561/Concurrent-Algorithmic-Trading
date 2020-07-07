from datetime import datetime
from pytz import timezone
from traceback import extract_stack

def warn(message, fileName=None):
    nyc = timezone('America/New_York')
    timestamp = datetime.now(nyc).strftime('%Y-%m-%d %H:%M:%S.%f')

    fileNames = ['warnings.log']
    if fileName is None: fileNames.append('warnings.log')

    stack = extract_stack().format()
    stack.pop() # remove warn()

    # print message to terminal
    print(timestamp + ' WARNING:', message)

    # write message and stack to files
    for fileName in fileNames:
        file = open(fileName, 'a')
        file.write(timestamp + ' WARNING: ' + message + '\n')
        for item in stack:
            file.write(item)
        file.write('\n')
        file.close()
