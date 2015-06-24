#coding: utf-8
import bs4
import bs4.element

import cgi
import urllib.request, urllib.error, urllib.parse
import math
import html5lib
import sys

__all__ = ["BodyTextExtraction"]

class Node:
    threshold = 0
    @classmethod
    def create(cls,soup_node):
        soup_node = Node._preprocess(soup_node)
        return Node._create(soup_node)

    @classmethod
    def _create(cls,soup_node):
        identity = lambda x:x

        if type(soup_node) == bs4.element.Tag or type(soup_node) == bs4.BeautifulSoup:
            valid_soup_children = list(filter(Node.is_valid_soupnode, soup_node.children))
            children = list(filter( identity, list(map(Node._create, valid_soup_children )) ))
            me = Node(soup_node, children)
            for child in me.children: #親ノードを設定する
                child.parent = me
            return me

        elif type(soup_node) == bs4.element.NavigableString:
            return Node(soup_node)
        else:
            pass #ignore all comments and others

    @classmethod
    def is_valid_soupnode(cls,soup):
        #return True
        if isinstance(soup, bs4.element.NavigableString):
            r = (True if (soup.string and soup.string.strip() ) else False)
            return (True if (soup.string and soup.string.strip() ) else False)
        else:
            return True

    @classmethod
    def _preprocess(cls,node):
        #unwrap tags
        merging_elements = ["p","br", "li","table","tbody","tr","td","theader","tfooter"]
        for element in merging_elements:
            tags = node.find_all(element)
            for tag in tags: 
                tag.unwrap()

        #remove tags
        ignored_elements = ["head","meta","script","link","style","form","option","header","footer","nav","noscript"]
        tags = node.find_all(ignored_elements)
        for tag in tags: tag.decompose()
        import re
        #tags = node.find_all([{style:"display:none"},{style:"display:none;"}])
        tags = node.find_all(style=re.compile("display:none;?"))
        for tag in tags: tag.decompose()

        def _merge_neighboring_navigablestrings(node):
            first_navigablestring = None
            for child in node.children:
                if type(child) == bs4.element.NavigableString:
                    if first_navigablestring:
                        first_navigablestring.string += child.string
                        child.string= ""
                    else:
                        first_navigablestring = child
                elif type(child) == bs4.element.Tag:
                    first_navigablestring = None
                    _merge_neighboring_navigablestrings(child)
                else:
                    first_navigablestring = None

        _merge_neighboring_navigablestrings(node)
        return node
        return bs4.BeautifulSoup(str(node))

    def __init__(self,soup,children=[]):
        self.soup = soup
        self.children = list(children)
        self.parent=None
        self.is_content = False

        self.extract_features()

    def show(self,depth=0,filtered=True):
        indent = "|  " * depth + "*"
        if self.is_navigable_string():
            #print(indent+"text", self.soup.string, " ctd=%f" % self.composite_text_density)
            print(indent+"text", self.soup.string)
        else:
            print(indent+"tag:",self.soup.name, self.soup.attrs, " ctd=%f" % self.composite_text_density, " ds=%f" % self.density_sum," content=%s" % self.is_content)

        for child in self.children: 
            child.show(depth+1)

    def is_navigable_string(self):
        return isinstance(self.soup, bs4.element.NavigableString)


    def extract_features(self):
        if self.is_navigable_string():
            self.characters = len(self.soup.string.strip())
            self.tags = 0

            self.link_characters = 0
            self.link_tags = 0
        else:
            self.characters = sum([n.characters for n in self.children])
            self.tags       = sum([n.tags for n in self.children]) 
            if not self.soup.name in ["div","span","p","br","li"]:
                self.tags += 1

            if self.soup.name == "a":
                self.link_characters = self.characters
                self.link_tags = 1
            else:
                self.link_characters = sum([n.link_characters for n in self.children])
                self.link_tags = sum([n.link_tags for n in self.children])


        self.text_density = 1.0 * max(self.characters,1) / max(self.tags, 1)

    def get_content_text(self):
        pass

    def mark_contents(self):
        body = self
        def _set_ctd(node):
            a = 1.0 * max(node.characters,1) * max(node.link_characters,1) / max(node.characters - node.link_characters,1)
            b = 1.0 * max(node.characters,1) * max(body.link_characters,1) / max(body.characters,1)

            base = math.log(a + b + math.e)
            antilog = 1.0 * max(node.characters,1) * max(node.tags,1) / max(node.link_characters,1) / max(node.link_tags,1)

            node.composite_text_density = node.text_density * math.log(antilog, base) #* math.log(max(node.characters,math.e))

        def _set_densitysum(node):
            if node.children and len(node.children) > 0:
                node.density_sum = sum([c.composite_text_density for c in node.children])
            else:
                node.density_sum = node.composite_text_density

        #calculate indexes
        for node in self.enumerate_dfs(): _set_ctd(node)
        for node in self.enumerate_dfs(): _set_densitysum(node)

        #find a node with max densitysum
        max_density_sum = float("-inf")
        node_with_max_density_sum = None
        for node in self.enumerate_dfs():
            if node.density_sum > max_density_sum:
                node_with_max_density_sum = node
                max_density_sum = node.density_sum

        #calculate threshold between content or noise
        path_to_the_node = node_with_max_density_sum.get_path()
        threshold_node = min(path_to_the_node, key=(lambda n:n.composite_text_density))
        threshold = threshold_node.composite_text_density

        self._mark_content_recursively(threshold)
        return threshold

    def _mark_content_recursively(self,threshold):
        self.threshold = threshold
        if self.composite_text_density >= threshold:
            best_child = self._get_node_with_best_density_sum()
            if best_child:
                best_child.is_content = True
            for child in self.children:
                child._mark_content_recursively(threshold)

    def _get_node_with_best_density_sum(self):
        best_node = None
        best_density_sum=float("-inf")
        for child in self.children:
            if child.is_navigable_string(): continue
            if best_density_sum <= child.density_sum:
                best_node = child
                best_density_sum = child.density_sum
        return best_node

    def enumerate_dfs(self):
        yield self
        for child in self.children:
            for c in child.enumerate_dfs():
                yield c

    def get_path(self):
        path = []
        cd = self
        while cd:
            path.append(cd)
            cd = cd.parent
        return path

class BodyTextExtraction:
    def __init__(self):
        pass

    def extract(self,html_content):
        soup = bs4.BeautifulSoup(html_content,"html5lib")
        body = soup.find("body")
        tree = Node.create(body)
        self.threshold = tree.mark_contents()
        self.tree=tree

        best_score = float("-inf")
        best_node = None
        for node in tree.enumerate_dfs():
            if node.is_navigable_string():    continue
            if not node.is_content:           continue
            if not node.soup.name in ["div","p"]: continue
            score = node.density_sum
            if score > best_score:
                best_node = node
                best_score = score

        self.best_node = best_node
        self.threshold = Node.threshold

        return best_node.soup.text.strip()

def get_unicode_content_from_url(url):
    response = urllib.request.urlopen(url)
    html_content = response.read()
    return html_content

if __name__=="__main__":
    argvs = sys.argv

    url = argvs[1]

    response = urllib.request.urlopen(url)
    html_content = response.read()

    extractor = BodyTextExtraction()
    text = extractor.extract(html_content)
    #extractor.tree.show()
    print(text.encode("utf-8"))

