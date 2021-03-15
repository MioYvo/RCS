# coding=utf-8
# __author__ = 'Mio'
from math import ceil

from sqlalchemy.orm import Query
from tornado.web import Finish

from utils.error_code import ERR_NO_CONTENT
from utils.http_code import HTTP_400_BAD_REQUEST


class PageFailedError(Finish):
    def __init__(self, error_code=0, msg="", content=None, status_code=400):
        chunk = dict(
            error_code=error_code,
            message=msg,
            content=content
        )
        # raise Finish Exception,tornado will call BaseRequestHandler.finish and pass args
        super(PageFailedError, self).__init__(chunk, status_code)


class Pagination(object):
    """Internal helper class returned by :meth:`BaseQuery.paginate`.  You
    can also construct it from any other SQLAlchemy query object if you are
    working with other libraries.  Additionally it is possible to pass `None`
    as query object in which case the :meth:`prev` and :meth:`next` will
    no longer work.
    """

    def __init__(self, query, page, per_page, total, items):
        #: the unlimited query object that was used to create this
        #: pagination object.
        self.query: Query = query
        #: the current page number (1 indexed)
        self.page: int = page
        #: the number of items to be displayed on a page.
        self.per_page: int = per_page
        #: the total number of items matching the query
        self.total: int = total
        #: the items for the current page
        self.items: Query = items

    @property
    def pages(self):
        """The total number of pages"""
        if self.per_page == 0 or self.total is None:
            pages = 0
        else:
            pages = int(ceil(self.total / float(self.per_page)))
        return pages

    def prev(self, error_out=False):
        """Returns a :class:`Pagination` object for the previous page."""
        assert self.query is not None, 'a query object is required ' \
                                       'for this method to work'
        return paginate(self.query, self.page - 1, self.per_page, error_out)

    @property
    def prev_num(self):
        """Number of the previous page."""
        if not self.has_prev:
            return None
        return self.page - 1

    @property
    def has_prev(self):
        """True if a previous page exists"""
        return self.page > 1

    def next(self, error_out=False):
        """Returns a :class:`Pagination` object for the next page."""
        assert self.query is not None, 'a query object is required ' \
                                       'for this method to work'
        return paginate(self.query, self.page + 1, self.per_page, error_out)

    @property
    def has_next(self):
        """True if a next page exists."""
        return self.page < self.pages

    @property
    def next_num(self):
        """Number of the next page"""
        if not self.has_next:
            return None
        return self.page + 1

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        """Iterates over the page numbers in the pagination.  The four
        parameters control the thresholds how many numbers should be produced
        from the sides.  Skipped page numbers are represented as `None`.
        This is how you could render such a pagination in the templates:
        .. sourcecode:: html+jinja
            {% macro render_pagination(pagination, endpoint) %}
              <div class=pagination>
              {%- for page in pagination.iter_pages() %}
                {% if page %}
                  {% if page != pagination.page %}
                    <a href="{{ url_for(endpoint, page=page) }}">{{ page }}</a>
                  {% else %}
                    <strong>{{ page }}</strong>
                  {% endif %}
                {% else %}
                  <span class=ellipsis>…</span>
                {% endif %}
              {%- endfor %}
              </div>
            {% endmacro %}
        """
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (self.page - left_current - 1 < num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num

    @property
    def count(self):
        return self.items.count()

    @property
    def php_meta_pagination(self):
        """
        For {
            ...
            "meta": {
                "pagination": {
                    "total": self.total,
                    "count": None,
                    "per_page": self.per_page,
                    "current_page": self.page,
                    "total_pages": self.pages,
                    "links": {}
                }
            }
        }
        Returns:

        """
        return {
            "total": self.total,
            "count": self.count,
            "per_page": self.per_page,
            "current_page": self.page,
            "total_pages": self.pages,
            "links": {}
        }


def paginate(query, page=1, per_page=20, error_out=True, max_per_page=None):
    """
    Returns a :class:`Pagination` object.
    """
    if max_per_page is not None:
        per_page = min(per_page, max_per_page)

    if page < 1:
        page = 1

    if per_page < 0:
        per_page = 20

    items = query.limit(per_page).offset((page - 1) * per_page)

    total = query.order_by(None).count()

    if not total and page != 1 and error_out:
        raise PageFailedError(error_code=ERR_NO_CONTENT, msg='no results', status_code=HTTP_400_BAD_REQUEST)

    return Pagination(query, page, per_page, total, items)
