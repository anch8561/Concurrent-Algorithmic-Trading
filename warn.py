from traceback import extract_stack
from marketHours import get_time

def warn(message, fileName=None):
    timestamp = get_time()

    fileNames = ['warnings.log']
    if fileName is None: fileNames.append('warnings.log')

    stack = extract_stack().format()
    stack.pop() # remove warn()

    # print to terminal
    print('WARNING:', message)
    for item in stack:
        print(item, end='')

    # write to files
    for fileName in fileNames:
        file = open(fileName, 'a')
        file.write(timestamp + ': WARNING: ' + message)
        for item in stack:
            file.write(item)
        file.close()