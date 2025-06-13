class Param:
    def __init__(self, clos_param):
        self.raw = clos_param
        self.name = clos_param["name"]
        self.parameter_kind = clos_param["parameterKind"]
        self.value = clos_param["textValue"]

    def stringify(self):
        return f"{self.name}={self.value}"

    def __repr__(self):
        print(self.raw)

    def __str__(self):
        print(f"Parameter: {self.name}. Vaule: {self.value}")


class DisplayParams:
    def __init__(self, clos_params):
        self.params = [Param(x) for x in clos_params]

    def stringify(self):
        return [x.stringify() for x in self.params]

    def __repr__(self):
        print("\n".join(self.params))

    def __str__(self):
        for param in self.params:
            print(param)
