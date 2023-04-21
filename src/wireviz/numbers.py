from dataclasses import dataclass, field
from math import modf
from typing import Any, Union

@dataclass
class NumberAndUnit:
    number: float
    unit: Union[str, None] = None

    @staticmethod
    def to_number_and_unit(
        inp: Any,
        default_unit: Union[str, None] = None,
        default_value: Union[float, None] = None,
    ):
        if inp is None:
            if default_value is not None:
                return NumberAndUnit(default_value, default_unit)
            return None
        elif isinstance(inp, NumberAndUnit):
            return inp
        elif isinstance(inp, float) or isinstance(inp, int):
            return NumberAndUnit(float(inp), default_unit)
        elif isinstance(inp, str):
            if " " in inp:
                number, unit = inp.split(" ", 1)
            else:
                number, unit = inp, default_unit
            try:
                number = float(number)
            except ValueError:
                raise Exception(
                    f"{inp} is not a valid number and unit.\n"
                    "It must be a number, or a number and unit separated by a space."
                )
            else:
                return NumberAndUnit(number, unit)

    def chose_unit(self, other):
        if self.unit is None:
            return other.unit

        if other.unit is not None and self.unit != other.unit:
            raise ValueError(f"Cannot add {self} and {other}, units not matching")
        return self.unit

    @property
    def number_str(self):
        return f"{self.number:.2f}" if modf(self.number)[0] else f"{int(self.number)}"

    @property
    def unit_str(self):
        return "" if self.unit is None else self.unit

    def __str__(self):
        return " ".join((self.number_str, self.unit_str)).strip()

    def __eq__(self, other):
        return self.number == other.number and self.unit == other.unit

    def __add__(self, other):
        other = NumberAndUnit.to_number_and_unit(other, self.unit, 0)

        return NumberAndUnit(
            number=float(self.number) + float(other.number),
            unit=self.chose_unit(other),
        )

    def __mul__(self, other):
        other = NumberAndUnit.to_number_and_unit(other, self.unit, 1)

        return NumberAndUnit(
            number=float(self.number) * float(other.number),
            unit=self.chose_unit(other),
        )
