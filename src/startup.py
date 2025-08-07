class StartUp:
    """Class to handle customer information (name, ID, phone)."""

    def __init__(self):
        """Initialize customer details with input."""
        print("Welcome To Our System")
        self.Name = input("Please, Enter your Name: ")  # Customer's name
        self.id = input("Enter Your National ID: ")     # Customer's national ID
        self.Phone = input("Enter your Phone Number: ") # Customer's phone number

    def DisPlayDetails(self):
        """Display customer details with borders."""
        border = "\n/// " + "=" * 100 + " ///"
        print(f"{border}\nWelcome MR: {self.Name}\nNational ID: {self.id}\nPhone Number: {self.Phone}{border}\n")
