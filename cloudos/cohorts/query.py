"""
Classes and functions that implement the query building syntax.
"""


class QueryComponent:
    """Class to provide logical operator methods for query-related child classes."""
    def __and__(self, other):
        """Overloads the bitwise AND operator '&' to perform logical AND operation.

        Returns
        -------
        Query
        """
        return and_(self, other)

    def __or__(self, other):
        """Overloads the bitwise OR operator '|' to perform logical OR operation.

        Returns
        -------
        Query
        """
        return or_(self, other)

    def __invert__(self):
        """Overloads the bitwise NOT operator '~' to perform logical NOT operation.

        Returns
        -------
        Query
        """
        return not_(self)


def and_(q1, q2):
    """Logical AND operation for combining two QueryComponent objects into a Query.

    Returns
    -------
    Query
    """
    if not (isinstance(q1, QueryComponent) and isinstance(q2, QueryComponent)):
        raise TypeError('inputs must be PhenoFilter or Query type')
    return Query('AND', [q2, q1])


def or_(q1, q2):
    """Logical OR operation for combining two QueryComponent objects into a Query.

    Returns
    -------
    Query
    """
    if not (isinstance(q1, QueryComponent) and isinstance(q2, QueryComponent)):
        raise TypeError('inputs must be PhenoFilter or Query type')
    return Query('OR', [q2, q1])


def not_(q1):
    """Logical NOT operation for a PhenoFilters/Query.

    Returns
    -------
    Query
    """
    if not isinstance(q1, QueryComponent):
        raise TypeError('input must be PhenoFilter or Query type')
    return Query('NOT', [q1])


class PhenoFilter(QueryComponent):
    """Class to represent a phenotype filter in a phenotype query.

    Parameters
    ----------
    field_id : int
        The field ID of the phenotype in the Cohort Browser.
    vals : list
        The list of selected values within the phenotype.
        Only for categorical phenotypes.
    vals_min : any
        The minimum value of the selected range within the phenotype.
        Only for continuous phenotypes.
    vals_max : any
        The maximum value of the selected range within the phenotype.
        Only for continuous phenotypes.
    """
    def __init__(self, pheno_id, vals=None, vals_min=None, vals_max=None):
        if vals is not None and vals_min is None and vals_max is None:
            pass
        elif vals_min is not None and vals_max is not None and vals is None:
            pass
        else:
            raise ValueError("Either 'vals' must be set or both "
                             "'vals_min' and 'vals_max' must be set.")

        self.pheno_id = pheno_id
        self.v_list = vals
        self.v_min = vals_min
        self.v_max = vals_max
        self.continuous = False if self.v_list else True

    @classmethod
    def from_api_dict(cls, pheno_dict):
        """Construct a PhenoFilter object using the response from the Cohort Browser API.
        Inverse of PhenoFilter.to_api_dict().

        Parameters
        ----------
        pheno_dict : dict
            A dict containing the phenotype information as produced by the API response.

        Returns
        -------
        PhenoFilter
        """
        pheno_id = pheno_dict['field']
        if 'from' in pheno_dict['value']:
            v_min = pheno_dict['value']['from']
            v_max = pheno_dict['value']['to']
            v_list = None
        else:
            v_min = None
            v_max = None
            v_list = pheno_dict['value']
        return cls(pheno_id, vals=v_list, vals_min=v_min, vals_max=v_max)

    def to_api_dict(self):
        """Create a dict containing phenotype infromation suitable for use with the Cohort Browser
        API. Inverse of PhenoFilter.from_api_dict().

        Returns
        -------
        dict
        """
        d = {'field': self.pheno_id,
             'instance': ['0'],
             'isLabel': False}
        if self.continuous:
            d['value'] = {'from': self.v_min,
                          'to': self.v_max}
        else:
            d['value'] = self.v_list
        return d

    def __repr__(self):
        if self.continuous:
            return f'PhenoFilter(pheno_id={self.pheno_id}, vals_min={self.v_min}, vals_max={self.v_max})'
        else:
            return f'PhenoFilter(pheno_id={self.pheno_id}, vals={self.v_list})'


class Query(QueryComponent):
    """Class to represent a phenotype query. Expected to be nested into a tree of
    queries/phenotypes.

    Parameters
    ----------
    operator : string
        The operator type of this node in the query.
    subqueries : list
        A list containing Query or PhenoFilter objects representing the subqueries nested within
        this query. i.e. the children of this node in the query tree.
    """
    def __init__(self, operator, subqueries):
        self.operator = operator
        self.subqueries = subqueries

    @classmethod
    def from_api_dict(cls, query_dict):
        """Construct a Query object using the response from the Cohort Browser API.
        Inverse of Query.to_api_dict().

        Parameters
        ----------
        query_dict: dict
            A dict containing the nested query information as produced by the API response.

        Returns
        -------
        Query
        """
        operator = query_dict['operator']
        subqueries = []
        for sub_dict in query_dict['queries']:
            if 'field' in sub_dict:
                subqueries.append(PhenoFilter.from_api_dict(sub_dict))
            else:
                subqueries.append(Query.from_api_dict(sub_dict))

        return cls(operator, subqueries)

    def to_api_dict(self):
        """Create a dict containing the nested query infromation suitable for use with the Cohort
        Browser API. Inverse of Query.from_api_dict().

        Returns
        -------
        dict
        """
        d = {'operator': self.operator,
             'queries': []}
        for item in self.subqueries:
            if isinstance(item, PhenoFilter):
                d['queries'].append(item.to_api_dict())
            elif isinstance(item, Query):
                d['queries'].append(item.to_api_dict())
        return d

    def list_phenofilters(self):
        """Return a flat list of all the PhenoFilter objects in the query.

        Returns
        -------
        list
        """
        pheno_list = []
        for item in self.subqueries:
            if isinstance(item, PhenoFilter):
                pheno_list.append(item)
            elif isinstance(item, Query):
                pheno_list += item.list_phenofilters()
            else:
                raise TypeError
        return pheno_list

    def strip_singletons(self, inplace=True):
        """Remove any redundant nodes in the nested query tree.

        Parameters
        ----------
        inplace: bool
            If True, modifies the existing Query object and returns None.
            If False, returns a new Query object with the redundant nodes removed.

        Returns
        -------
        None | Query
        """
        # Beware, this function is recursive!

        if inplace:
            # leave the current object intact and only modify the subqueries

            subqueries = []
            for sq in self.subqueries:
                if isinstance(sq, PhenoFilter):
                    subqueries.append(sq)
                else:
                    subqueries.append(sq.strip_singletons(inplace=False))
            self.subqueries = subqueries

        else:
            # return new Query objects recursively

            if len(self.subqueries) < 2 and self.operator != 'NOT':
                # this is a redundant node so just return the subquery
                if isinstance(self.subqueries[0], PhenoFilter):
                    return self.subqueries[0]
                else:
                    return self.subqueries[0].strip_singletons(inplace=False)

            else:
                # this is not a redundant node so construct and return
                # a copy of itself with the function applied recursively
                subqueries = []
                for sq in self.subqueries:
                    if isinstance(sq, PhenoFilter):
                        subqueries.append(sq)
                    else:
                        subqueries.append(sq.strip_singletons(inplace=False))
                return Query(self.operator, subqueries)

    def __repr__(self):
        result = f"Query('{self.operator}', [\n"
        for i, sq in enumerate(self.subqueries):
            if i < len(self.subqueries) - 1:
                result += f'{sq},\n'
            else:
                result += f'{sq}\n'
        result += '])\n'

        r_l = result.splitlines()
        result = '\n'.join(r_l[:1] + ['    '+s for s in r_l[1:-1]] + r_l[-1:])

        return result
