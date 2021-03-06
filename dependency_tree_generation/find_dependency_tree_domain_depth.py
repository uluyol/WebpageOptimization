from argparse import ArgumentParser
from urlparse import urlparse

import common_module
import os
import simplejson as json

def main(root_dir):
    pages = os.listdir(root_dir)
    for page in pages:
        dependency_tree_filename = os.path.join(root_dir, page)
        page = get_page_name(page)
        try:
            tree_depth = find_dependency_tree_depth(dependency_tree_filename, page)
            if tree_depth > 0:
                print '{0} {1} {2}'.format(page, tree_depth[0], tree_depth[1])
        except RuntimeError as e:
            pass

def find_dependency_tree_depth(dependency_tree_filename, page):
    with open(dependency_tree_filename, 'rb') as input_file:
        dependency_tree = json.load(input_file)
    root_node = find_root_node(page, dependency_tree)
    if root_node is not None:
        return bfs(dependency_tree, None, root_node, 0)
    return -1

def bfs(dependency_tree, parent_node, current_node, current_depth):
    max_depth = (current_depth, current_node['url'])
    if current_node['isLeaf']:
        return max_depth

    children = set(current_node['children'])
    for child in children:
        if not child.startswith('data') and current_node is not None:
            child_node = dependency_tree[child]
            if parent_node is not None:
                # print 'parent: {0} current: {1} depth: {2}'.format(parent_node['url'], child_node['url'], current_depth)
                pass
            if child.startswith('data'):
                return max_depth
            elif parent_node is None:
                max_depth = max(max_depth, bfs(dependency_tree, current_node, child_node, current_depth + 1), key=lambda x: x[0])
            else:
                parsed_current_node = urlparse(current_node['url'])
                parsed_parent_node = urlparse(parent_node['url'])
                next_depth = current_depth + 1 if parsed_current_node.netloc != parsed_parent_node.netloc else current_depth
                max_depth = max(max_depth, bfs(dependency_tree, current_node, child_node, next_depth), key=lambda x: x[0])
    return max_depth

def find_root_node(page, dependency_tree):
    for node in dependency_tree:
        escaped_page = common_module.escape_url(node)
        if escaped_page == page:
            return dependency_tree[node]
    return None

def get_page_name(page_with_json_suffix):
    return page_with_json_suffix[:len(page_with_json_suffix) - len('.json')]

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('root_dir')
    args = parser.parse_args()
    main(args.root_dir)
