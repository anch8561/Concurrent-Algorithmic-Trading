from datetime import datetime
from pytz import timezone
from traceback import extract_stack

def warn(message, extraInfo=None, fileName=None):
    nyc = timezone('America/New_York')
    timestamp = datetime.now(nyc).strftime('%Y-%m-%d %H:%M:%S.%f')

    fileNames = ['warnings.log']
    if fileName: fileNames.append(fileName)

    stack = extract_stack().format()
    stack.pop() # remove warn()

    # print message to terminal
    print('WARNING: ' + timestamp)
    print(message)
    print(stack[-1])

    # write message and stack to files
    for fileName in fileNames:
        file = open(fileName, 'a')
        file.write('WARNING: ' + timestamp + '\n')
        file.write(message + '\n')
        if extraInfo: file.write(extraInfo + '\n')
        for item in stack:
            file.write(item)
        file.write('\n')
        file.close()
