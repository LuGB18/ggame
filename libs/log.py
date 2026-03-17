
def log(text:tuple, type='mod'):
    match type:
        case 'mod':
            print(f'PR:{text[0]}, MOD:{text[1]}, CHANGED:{text[2]}, FROM:{text[3]}')
        case 'modloadingerror':
            return f'PR:{text[0]}, MOD:{text[1]}, CHANGED:{text[2]}, FROM:{text[3]} WHERE VARIABLE WAS NOT FOUND.'
