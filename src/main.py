from database import Database
from managing_system import ManagingSystem

def main():
    """Main application entry point"""
    db = Database()                 # Initialize the database connection and create tables
    system = ManagingSystem()      # Initialize the management system object

    while True:
        system.display_menu()      # Show the menu options to the user
        choice = input("Select option (1-5): ")  # User selects an option

        if choice == "1":
            system.add_car(db)     # Add a new car to the database
        elif choice == "2":
            system.view_all_cars(db)  # Display all cars
        elif choice == "3":
            system.search_cars(db)    # Search for cars by make
        elif choice == "4":
            system.update_car(db)     # Update car information
        elif choice == "5":
            print("Exiting system...")  # Exit the application
            break
        else:
            print("Invalid choice! Please enter 1-5")  # Handle invalid input

# Ensure main() only runs if this script is executed directly
if __name__ == "__main__":
    main()
