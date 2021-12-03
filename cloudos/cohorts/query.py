"""
Classes that implement the query building syntax.
"""


class Phenotype:
    def __init__(self, field_id, vals=None, vals_min=None, vals_max=None):
        self.field = field_id
        self.v_list = vals
        self.v_min = vals_min
        self.v_max = vals_max
        self.continuous = False if self.v_list else True

    @classmethod
    def from_dict(cls, pheno_dict):
        field = pheno_dict['field']
        if 'from' in pheno_dict['value']:
            v_min = pheno_dict['value']['from']
            v_max = pheno_dict['value']['to']
            v_list = None
        else:
            v_min = None
            v_max = None
            v_list = pheno_dict['value']
        return cls(field, vals=v_list, vals_min=v_min, vals_max=v_max)

    def to_api_dict(self):
        d = {'field': self.field,
             'instance': ['0'],
             'isLabel': False}
        if self.continuous:
            d['value'] = {'from': self.v_min,
                          'to': self.v_max}
        else:
            d['value'] = self.v_list
        return d

    def __and__(self, other):
        return and_(self, other)

    def __or__(self, other):
        return or_(self, other)

    def __invert__(self):
        return not_(self)

    def __repr__(self):
        if self.continuous:
            return f'Phenotype(field_id={self.field}, vals_min={self.v_min}, vals_max={self.v_max})'
        else:
            return f'Phenotype(field_id={self.field}, vals={self.v_list})'


class Query:
    def __init__(self, operator, subqueries):
        self.operator = operator
        self.subqueries = subqueries

    @classmethod
    def from_dict(cls, query_dict):
        operator = query_dict['operator']
        subqueries = []
        for sub_dict in query_dict['queries']:
            if 'field' in sub_dict:
                subqueries.append(Phenotype.from_dict(sub_dict))
            else:
                subqueries.append(Query.from_dict(sub_dict))

        return cls(operator, subqueries)

    def list_phenotypes(self):
        pheno_list = []
        for item in self.subqueries:
            if type(item) == Phenotype:
                pheno_list.append(item)
            elif type(item) == Query:
                pheno_list += item.list_phenotypes()
            else:
                raise TypeError
        return pheno_list

    def to_api_dict(self):
        d = {'operator': self.operator,
             'queries': []}
        for item in self.subqueries:
            if type(item) == Phenotype:
                d['queries'].append(item.to_api_dict())
            elif type(item) == Query:
                d['queries'].append(item.to_api_dict())
        return d

    def strip_singletons(self, inplace=True):
        if inplace:
            subqueries = []
            for sq in self.subqueries:
                if type(sq) == Phenotype:
                    subqueries.append(sq)
                else:
                    subqueries.append(sq.strip_singletons(inplace=False))
            self.subqueries = subqueries

        else:
            if len(self.subqueries) == 1 and self.operator != 'NOT':
                if type(self.subqueries[0]) == Phenotype:
                    return self.subqueries[0]
                else:
                    return self.subqueries[0].strip_singletons(inplace=False)
            else:
                subqueries = []
                for sq in self.subqueries:
                    if type(sq) == Phenotype:
                        subqueries.append(sq)
                    else:
                        subqueries.append(sq.strip_singletons(inplace=False))
                return Query(self.operator, subqueries)

    def __and__(self, other):
        return and_(self, other)

    def __or__(self, other):
        return or_(self, other)

    def __invert__(self):
        return not_(self)

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


def and_(q1, q2):
    return Query('AND', [q2, q1])


def or_(q1, q2):
    return Query('OR', [q2, q1])


def not_(q1):
    return Query('NOT', [q1])
