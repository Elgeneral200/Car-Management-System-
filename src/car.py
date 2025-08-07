'''
This module defines a Car class that represents a car with various attributes and methods to add details and display them.
'''

class Car:
    def __init__(self):
        # Basic car attributes
        self.make = ""
        self.model = ""
        self.color = ""
        self.year = 0
        self.price = ""
        self.type = ""  # e.g. SUV, Sedan
        self.condition = ""  # e.g. New, Used
        self.drive_trains = ""  # e.g. AWD, FWD
        self.engine_power = 0  # in CC
        self.liter_capacity = 0  # Engine capacity in liters

        # Assigned salesperson (default if not assigned)
        self.salesperson_car = "No Salesperson assigned for this car"

    def add_car_details(self):
        # Collecting car details from user input
        self.make = input("Make: ")
        self.model = input("Model: ")
        self.color = input("Color: ")
        self.year = int(input("Year: "))
        self.price = input("Price: ")
        self.type = input("Type: ")
        self.condition = input("Condition: ")
        self.drive_trains = input("Drive Trains: ")
        self.engine_power = int(input("Engine power (CC): "))
        self.liter_capacity = int(input("Liter Capacity (L): "))

    def display_car(self):
        # Printing the car's details in a formatted way
        print("\n/// ==================================================================================================== ///")
        print(f"Make: {self.make} \tModel: {self.model} \tColor: {self.color} \tYear: {self.year} \tPrice: {self.price} EGP \tSalesperson: {self.salesperson_car}")
        print(f"Type: {self.type} \tCondition: {self.condition} \tDrive Trains: {self.drive_trains} \tEngine Power: {self.engine_power} CC \tLiter Capacity: {self.liter_capacity} L")
        print("/// ==================================================================================================== ///\n")

    def return_make(self):
        # Return the make of the car (useful for searching or filtering)
        return self.make
