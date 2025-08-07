class Vehicle:
    """Base class for vehicle properties"""

    def __init__(self):
        """Initialize common vehicle attributes"""
        self.make = ""         # Manufacturer name
        self.model = ""        # Model name
        self.year = 0          # Year of manufacture
        self.price = 0.0       # Price of the vehicle
        self.color = ""        # Color of the vehicle

    def input_basic_info(self):
        """Collect basic vehicle information from user"""
        self.make = input("Manufacturer (Make): ")
        self.model = input("Model: ")
        self.year = int(input("Year: "))
        self.price = float(input("Price: "))
        self.color = input("Color: ")

    def get_basic_info(self):
        """Return basic info as dictionary"""
        return {
            'make': self.make,
            'model': self.model,
            'year': self.year,
            'price': self.price,
            'color': self.color
        }


class Car(Vehicle):
    """Extended class with car-specific properties"""

    def __init__(self):
        super().__init__()  # Inherit base vehicle attributes
        self.type = ""             # Type of vehicle (e.g., SUV, Sedan)
        self.condition = ""        # Condition (New, Used)
        self.drive_trains = ""     # Drive system (e.g., FWD, AWD)
        self.engine_power = 0      # Engine power in CC
        self.liter_capacity = 0    # Fuel tank capacity in liters
        self.salesperson = ""      # Salesperson assigned to the car

    def input_full_info(self):
        """Collect complete car information"""
        self.input_basic_info()  # Get base info from parent class
        self.type = input("Vehicle Type (SUV/Sedan/etc): ")
        self.condition = input("Condition (New/Used): ")
        self.drive_trains = input("Drive Trains: ")
        self.engine_power = int(input("Engine Power (CC): "))
        self.liter_capacity = int(input("Fuel Capacity (Liters): "))
        self.salesperson = input("Assigned Salesperson: ")

    def get_full_info(self):
        """Return all car data as dictionary"""
        info = self.get_basic_info()  # Start with base vehicle info
        info.update({
            'type': self.type,
            'condition': self.condition,
            'drive_trains': self.drive_trains,
            'engine_power': self.engine_power,
            'liter_capacity': self.liter_capacity,
            'salesperson': self.salesperson
        })
        return info

    def display(self):
        """Print formatted car information"""
        print("\n" + "="*50)
        print(f"{self.year} {self.make} {self.model}")
        print(f"Color: {self.color}\tPrice: ${self.price:,.2f}")
        print(f"Type: {self.type}\tCondition: {self.condition}")
        print(f"Engine: {self.engine_power}cc\tFuel Capacity: {self.liter_capacity}L")
        print(f"Salesperson: {self.salesperson}")
        print("="*50)
