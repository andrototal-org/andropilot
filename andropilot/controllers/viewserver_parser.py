import logging

logger = logging.getLogger('viewserver')


class Rect:
    mLeft = 0
    mRight = 0
    mTop = 0
    mBottom = 0


class Point:
    x = 0
    y = 0


def convert_int(value):
    return int(value)


def convert_bool(value):
    if value == 'true':
        return True
    else:
        return False


def convert_visibility(value):
    values = {
        'GONE': None,
        'INVISIBLE': False,
        'VISIBLE': True,
    }
    try:
        value = values[value]
    except:
        value = None
    return value


def convert_text(value):
    return value

conversion_table = {
    'mID': convert_text,
    'mText': convert_text,
    'mLeft': convert_int,
    'mRight': convert_int,
    'mTop': convert_int,
    'mBottom': convert_int,
    'getWidth()': convert_int,
    'getHeight()': convert_int,
    'mScrollX': convert_int,
    'mScrollY': convert_int,
    'mPaddingLeft': convert_int,
    'mPaddingRight': convert_int,
    'mPaddingTop': convert_int,
    'mPaddingBottom': convert_int,
    'layout_leftMargin': convert_int,
    'layout_rightMargin': convert_int,
    'layout_topMargin': convert_int,
    'layout_bottomMargin': convert_int,
    'getBaseline()': convert_int,
    'willNotDraw()': convert_bool,
    'hasFocus()': convert_bool,
    'isClickable()': convert_bool,
    'isEnabled()': convert_bool,
    'getVisibility()': convert_visibility
}


class VSNode(object):

    rawData = ""
    mClassName = "mClassName"
    mHashCode = "fffff"
    mId = ""
    mText = "mText"
    mAbsoluteRect = Rect()
    mRect = Rect()
    mLocation = Point()
    mParentNode = {}
    mChildNodes = []
    mDepth = 0
    # currently, I get this value from (DRAWN, Visiable, Clickable)
    mActive = False
    mVisible = False
    mScrollX = 0
    mScrollY = 0
    mClickable = False

    def get_all_children(self):
        children = self.mChildNodes
        for c in self.mChildNodes:
            children = children + c.get_all_children()

        return children

    def get_children_by_id(self, id):
        real_id = 'id/' + id
        children = []
        for c in self.mChildNodes:
            if c.mId == real_id:
                children.append(c)
            children = children + c.get_children_by_id(id)

        return children

    def get_center_point(self):
        (left, top, right, bottom) = self.get_absolute_rect()
        # get the center point
        x = self.mLeft + int((right + left) / 2)
        y = self.mTop + int((bottom + top) / 2)
        return (x, y)

    def get_absolute_rect(self):
        abs_left = self.mLeft
        abs_top = self.mTop

        p = self.mParentNode
        # go up till the root node
        while p is not None:
            abs_left += p.mLeft - p.mScrollX
            abs_top += p.mTop - p.mScrollY
            p = p.mParentNode

        abs_right = abs_left + self.mRight - self.mLeft
        abs_bottom = abs_top + self.mBottom - self.mTop

        return (abs_left, abs_top, abs_right, abs_bottom)

    def __str__(self):
        return self.mId + ' ' + self.mClassName

    @classmethod
    def _create_node_from_data(cls, data=''):
        # create a new node to be filled with the parsed data
        node = cls()
        node.rawData = data

        class_name_hashcode, sep, properties = data.partition(' ')

        # set the node class name and hashcode
        (node.mClassName, sep,
            hashCode) = class_name_hashcode.partition('@')

        if not hashCode:
            logger.error(
                "could not parse class name/hashcode, offending data: %s",
                data)
            return None

        try:
            node.mHashCode = long(hashCode, 16)
        except:
            node.mHashCode = hashCode

        # parse all the properties
        while True:
            # get the property name
            property_name, sep, properties = properties.partition('=')
            if property_name == '' or sep == '':
                break

            (property_category, sep, property_name
             ) = property_name.partition(':')

            property_name = property_name.strip()
            property_category = property_category.strip()
            if property_name == '':
                property_name = property_category

            # get the property value length
            length, sep, properties = properties.partition(',')

            length = int(length)

            # decode utf-8 names
            # in utf-8 we can have at most 3/4 bytes for each char
            # read at most lenght*4
            if property_name == 'mText':
                l = min(len(properties), length * 4)
                value = properties[:l].decode('utf8')
                value = value[:length]
                length = len(str(value.encode('utf-8')))
            else:
                # get the property value
                value = properties[:length]
            properties = properties[length:]
            try:
                setattr(
                    node, property_name.rstrip('()'),
                    conversion_table[property_name](value))
            except:
                # this value is not interesting to us...
                continue

        def _set_value(node, name, source_name, default):
            try:
                val = getattr(node, source_name)
            except:
                val = default

            node.__setattr__(name, val)

        # set some defaults
        _set_value(node, 'baseline', 'getBaseline', 0)
        _set_value(node, 'width', 'getWidth', 0)
        _set_value(node, 'height', 'getHeight', 0)
        _set_value(node, 'mVisible', 'getVisibility', False)
        _set_value(node, 'mId', 'mID', '')

        return node
        # node.mActive = TODO


def build_tree(dump_data):
    list_data = dump_data.split("\n")

    # try to pop the last 2 elements "DONE" and "DONE."
    try:
        list_data.remove("DONE")
    except:
        pass
    try:
        list_data.remove("DONE.")
    except:
        pass

    elements_indents_list = []

    for element in list_data:
        indent = 0
        # 1 space = 1 node depth
        try:
            while element[indent] == ' ':
                indent = indent + 1
        except IndexError:
            continue

        elements_indents_list.append((indent, element))

    # elements_indents_list is a list of pairs,
    # i.e. [(element_indentation, element) ...]
    tree_nodes_list = []

    for idx, (depth, el) in enumerate(elements_indents_list):
        # the depth of the node is given by its indentation
        node = VSNode._create_node_from_data(el.strip())
        if node is None:
            logger.error("empty node parsed from %s", el)
            continue
        node.mDepth = depth
        node.mChildNodes = []

        if depth == 0:
            # it is a root node, no parent node
            node.mParentNode = None
        else:
            pre_idx = idx - 1
            delta_depth = depth - tree_nodes_list[pre_idx].mDepth

            if delta_depth == 1:
                # current node is a child node of the last visited node
                node.mParentNode = tree_nodes_list[pre_idx]

            elif delta_depth == 0:
                # these two nodes have same depth, so that they have same
                # parent node
                node.mParentNode = tree_nodes_list[pre_idx].mParentNode

            elif delta_depth < 0:
                reversed_nodes = enumerate(reversed(tree_nodes_list))
                brother_distance = 1 + \
                    next(i for i, n in reversed_nodes if n.mDepth == depth)
                node.mParentNode = tree_nodes_list[
                    idx - brother_distance].mParentNode

            else:
                raise Exception(
                    "Some problem occurred while building the view tree")
                break

            node.mParentNode.mChildNodes.append(node)

        # set node real visibility
        if node.mParentNode:
            node.isShown = node.mParentNode.isShown
        else:
            node.isShown = node.mVisible

        tree_nodes_list.append(node)

    # return the built tree as a list of VSNode
    return tree_nodes_list


# EXPERIMENTAL #
def get_dot_graph(tree_nodes_list):
    dot_graph = ""
    for node in tree_nodes_list:
        dot_line = node.mHashCode + ";\n"
        while node.mParentNode is not None:
            dot_line = node.mParentNode.mHashCode + " -> " + dot_line
            node = node.mParentNode
        dot_graph += dot_line
    dot_graph = "{" + dot_graph + "}"

    return dot_graph
