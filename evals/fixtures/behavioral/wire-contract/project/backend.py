import json
import sys

def receipt(total_cents):
    return {'amount': total_cents, 'currency': 'USD'}

if __name__ == '__main__':
    print(json.dumps(receipt(int(sys.argv[1]))))
