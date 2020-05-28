from traceback import extract_stack

def warn(message, fileName=None):
    # TODO: add timestamp

    # check arguments
    if fileName is None: fileNames = ('warnings.log')
    else: fileNames = (fileName, 'warnings.log')

    stack = extract_stack().format()
    stack.pop() # remove warn()

    # print to terminal
    print('WARNING:', message)
    for item in stack:
        print(item, end='')

    # write to files
    for fileName in fileNames:
        file = open(fileName, 'a')
        file.write('WARNING: ' + message)
        for item in stack:
            file.write(item)
        file.close()