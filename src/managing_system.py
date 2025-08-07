from vehicle import Car

class ManagingSystem:
    """Core system for managing car inventory operations"""

    def __init__(self):
        """Initialize management system"""
        self.current_selection = None  # Placeholder for menu interaction (optional)

    def display_menu(self):
        """Display main system menu"""
        print("\n" + "="*50)
        print("Car Sales Management System")
        print("1. Add New Car")
        print("2. View All Cars")
        print("3. Search Cars by Make")
        print("4. Update Car Details")
        print("5. Exit")
        print("="*50)

    def add_car(self, db):
        """Add new car to database"""
        car = Car()
        car.input_full_info()  # Collect all car data from user
        
        data = car.get_full_info()  # Get the car data as a dictionary
        query = """
        INSERT INTO cars 
        (make, model, year, price, color, type, condition, 
         drive_trains, engine_power, liter_capacity, salesperson) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        db.execute_query(query, tuple(data.values()))  # Insert into database
        print("Car added successfully!")

    def view_all_cars(self, db):
        """Display all cars in database"""
        cars = db.fetch_cars()  # Should return a list of tuples (car records)
        if not cars:
            print("No cars in inventory!")
            return
        
        print("\n" + "="*50)
        print(f"Displaying {len(cars)} cars:")
        for car in cars:
            # Basic display of key car attributes
            print(f"\nID: {car[0]} | {car[1]} {car[2]} ({car[3]})")
            print(f"Price: ${car[4]:,.2f} | Color: {car[5]}")
        print("="*50)

    def search_cars(self, db):
        """Search cars by manufacturer"""
        make = input("Enter manufacturer name: ")
        cars = db.fetch_cars(make)  # Assuming this filters by make
        
        if not cars:
            print(f"No {make} cars found!")
            return
        
        print(f"\nFound {len(cars)} {make} car(s):")
        for car in cars:
            print(f"\nID: {car[0]}")
            print(f"Model: {car[2]} ({car[3]})")
            print(f"Price: ${car[4]:,.2f} | Type: {car[6]}")
            print(f"Salesperson: {car[10]}")

    def update_car(self, db):
        """Update existing car record"""
        car_id = input("Enter car ID to update: ")

        # Check if the car with this ID exists
        existing = db.execute_query("SELECT * FROM cars WHERE id=?", (car_id,)).fetchone()
        if not existing:
            print("Invalid car ID!")
            return

        print(f"\nUpdating: {existing[1]} {existing[2]}")
        print("Leave blank to keep current value")

        # Define which fields can be updated
        updates = {}
        fields = [
            ('make', 'Manufacturer', str),
            ('model', 'Model', str),
            ('year', 'Year', int),
            ('price', 'Price', float),
            ('color', 'Color', str)
        ]

        # Prompt user for each field; update only if not empty
        for field, prompt, dtype in fields:
            current_value = existing[fields.index((field, prompt, dtype)) + 1]
            new_val = input(f"{prompt} [{current_value}]: ")
            if new_val:
                updates[field] = dtype(new_val)

        if updates:
            # Build dynamic SQL update query
            set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
            query = f"UPDATE cars SET {set_clause} WHERE id=?"
            params = list(updates.values()) + [car_id]
            db.execute_query(query, params)
            print("Update successful!")
        else:
            print("No changes made.")
