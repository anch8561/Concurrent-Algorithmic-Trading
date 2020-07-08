from datetime import datetime
from pytz import timezone
from traceback import extract_stack

def warn(message, extraInfo=None, fileName=None):
    # check arguments
    message = str(message)
    if extraInfo: extraInfo = str(extraInfo)
    if fileName: fileName = str(fileName)

    # get timestamp
    nyc = timezone('America/New_York')
    timestamp = datetime.now(nyc).strftime('%Y-%m-%d %H:%M:%S.%f')

    # get filenames
    fileNames = ['warnings.log']
    if fileName: fileNames.append(fileName)

    # get stack
    stack = extract_stack().format()
    stack.pop() # remove warn()

    # print message to terminal
    print('WARNING: ' + message)
    print(timestamp)
    print(stack[-1])

    # write message and stack to files
    for fileName in fileNames:
        with open(fileName, 'a') as f:
            f.write(timestamp + ' WARNING: ' + message + '\n')
            if extraInfo: f.write(extraInfo + '\n')
            for item in stack:
                f.write(item)
            f.write('\n')
