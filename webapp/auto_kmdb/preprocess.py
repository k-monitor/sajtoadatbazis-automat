import re
from urllib.parse import urlparse


def clear_url(url):
    """
    Clears the URL by removing .www and any trailing slashes.

    Args:
        url (str): The URL to be cleared.

    Returns:
        str: The cleared URL.
    """
    u = urlparse(url)
    return u.scheme + '://' + u.netloc + '/' + u.path.replace('www.', '').strip('/')


def read_file(filename):
    with open(filename, 'r') as f:
        return f.readlines()


def do_replacements(text, replacements):
    """
    Replace all occurrences of patterns in a string with their corresponding replacements.

    Parameters:
        text (str): The input string.
        replacements (dict): A dictionary of patterns and their corresponding replacements.

    Returns:
        str: The output string with all occurrences of patterns replaced.
    """
    for pattern, replacement in replacements:
        text = pattern.sub(replacement, text)
    return text


common_descriptions = read_file('auto_kmdb/data/common_descriptions.txt')
common_lines = read_file('auto_kmdb/data/common_lines.txt')

picture_pattern = re.compile(r'Fotó: (\w+\/[^\s]+ [^\s]+|MTI)')
picture_pattern = re.compile(r'Fotó: .*')
quote_pattern = re.compile(r'[”“„]')
dot_pattern = re.compile(r'[…]')
line_pattern = re.compile(r'^\d{4}\. [^\s]+ \d{2}\., [^\s]+, \d{2}\:\d{2} • .*$|(^Szerző: .*$)|(^Címkék: .*$)|(^Kiemelt kép: .*$)')
space_pattern = re.compile(r'  +')
newline_pattern = re.compile(r'\n\n+')
dash_pattern = re.compile(r'\–')
photo_camera_pattern = re.compile(r'photo_camera*')

replacements = [(picture_pattern, ''), (quote_pattern, '"'),
                (dot_pattern, '...'), (line_pattern, ''),
                (space_pattern, ' '), (dash_pattern, '-'),
                (photo_camera_pattern, ''), (newline_pattern, '\n\n')]
