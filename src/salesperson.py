class Salesperson:
    """Class to store salesperson details (name, phone, car brand they sell)."""

    def __init__(self, name=" ", phone="0", make=" "):
        """Initialize salesperson data."""
        self.name = name
        self.Phone_Number = phone
        self.Make_Person = make

    def DisplayCarPerson(self):
        """Print salesperson info with formatted borders."""
        border = "\n/// " + "=" * 100 + " ///"
        print(f"{border}\nSeller Name: {self.name}\tPhone Number: {self.Phone_Number}\nSales Person For: {self.Make_Person}{border}\n")