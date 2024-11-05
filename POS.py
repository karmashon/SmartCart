import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window
import sqlite3

Window.clearcolor = (1,1,1,1)

kivy.require('2.1.0')  # Replace with your Kivy version

class POSApp(App):
    def build(self):
        # Initialize database & query cursor
        connection = sqlite3.connect("marketDB.db")
        self.cursor = connection.cursor()

        # Drop table only if changes need to be made
        #self.cursor.execute("Drop table if exists Items")
        
        self.cursor.execute(
            "Create table if not exists Items(itemID integer primary key, itemName text, itemPrice real, itemCode text)"
            )

        # Hardcoded item arrays
        item_codes = {"12345" : "Item 1", "23456" : "Item 2", "34567" : "Item 3", "45678" : "Item 4",
                           "56789" : "Item 5", "67890" : "Item 6", "78901" : "Item 7"}
        prices = {'Item 1' : 10.0, 'Item 2' : 20.0, 'Item 3' : 30.0, 'Item 4' : 40.0, 'Item 5' : 50.0, 
                       'Item 6' : 60.0, 'Item 7' : 70.0}
        barcodes = {'Item 1' : "12345678901234", 'Item 2' : "23456789012345", 'Item 3' : "34567890123456", 'Item 4' : 
                    "45678901234567", 'Item 5' : "56789012345678", 'Item 6' : "67890123456789", 'Item 7' : "78901234567890"}
        
        # Save items into database if it is a new item
        for id in item_codes:
            existCount = self.cursor.execute("Select Count(*) from Items where itemID = "+id)
            if existCount.fetchone()[0]==0:
                self.cursor.execute(
                    "Insert into Items values("+id+",\'"+str(item_codes[id])+"\',"+str(prices[item_codes[id]])+",\'"+barcodes[item_codes[id]]+"\')"
                )
        
        # Display records for verifying table creation and insertion
        tableRecords = self.cursor.execute("Select * from Items").fetchall()
        for record in tableRecords:
            print(record)

        
        self.barcode_buffer = ""  # Variable to store the barcode input
        self.keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self.keyboard.bind(on_key_down=self._on_keyboard_down)

        root = BoxLayout(orientation='vertical')
        main_layout = BoxLayout(orientation='horizontal')

        # Left half: Item list
        left_layout = BoxLayout(orientation='vertical')
        left_scroll = ScrollView(size_hint=(1, None), size=(400, 600))
        left_grid = GridLayout(cols=1, padding=10, spacing=10, size_hint_y=None)
        left_grid.bind(minimum_height=left_grid.setter('height'))

        # Add some items to the left side
        
        for item in tableRecords:
            btn = Button(text=item[1]+", MRP : "+str(item[2]), size_hint_y=None, height=40)
            btn.bind(on_release=self.add_to_cart)
            left_grid.add_widget(btn)

        left_scroll.add_widget(left_grid)
        left_layout.add_widget(left_scroll)
        
        # Right half: Cart
        right_layout = BoxLayout(orientation='vertical')
        right_scroll = ScrollView(size_hint=(1, None), size=(400, 600))
        self.right_grid = GridLayout(cols=1, padding=10, spacing=10, size_hint_y=None)
        self.right_grid.bind(minimum_height=self.right_grid.setter('height'))

        right_scroll.add_widget(self.right_grid)
        right_layout.add_widget(right_scroll)

        self.price_label = Label(text="Total Price : 0.00", size_hint_y=None, height=40, color=(0, 0, 0, 1))

        main_layout.add_widget(left_layout)
        main_layout.add_widget(right_layout)
        
        root.add_widget(main_layout)
        root.add_widget(self.price_label)

        # To store items and their quantities
        self.cart_items = {}
        self.total_price = 0.00

        return root

    def add_to_cart(self, instance):
        item_name = instance.text.split(',')[0]
        item_price = self.cursor.execute("Select itemPrice from Items where itemName = \'"+item_name+"\'").fetchone()[0]

        # Check if the item is already in the cart
        if item_name in self.cart_items:
            self.increment_quantity(item_name)
        else:
            # Create a new entry in the cart
            item_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)

            item_label = Label(text=item_name, size_hint_x=0.6, color=(0,0,0,1))
            quantity_label = Label(text='1', size_hint_x=0.2, color=(0,0,0,1))
            price_label = Label(text='X '+str(item_price), size_hint_x=0.6, color=(0,0,0,1))
            
            # Add + and - buttons
            plus_button = Button(text='+', size_hint_x=0.1)
            plus_button.bind(on_release=lambda btn: self.increment_quantity(item_name))

            minus_button = Button(text='-', size_hint_x=0.1)
            minus_button.bind(on_release=lambda btn: self.decrement_quantity(item_name))

            item_layout.add_widget(item_label)
            item_layout.add_widget(minus_button)
            item_layout.add_widget(quantity_label)
            item_layout.add_widget(plus_button)
            item_layout.add_widget(price_label)

            self.right_grid.add_widget(item_layout)

            # Store the item info in the cart dictionary
            self.cart_items[item_name] = {'quantity': 1, 'quantity_label': quantity_label}
            self.update_total(item_price)

    def increment_quantity(self, item_name):
        item_info = self.cart_items[item_name]
        item_info['quantity'] += 1
        item_info['quantity_label'].text = str(item_info['quantity'])
        addedItemCost = self.cursor.execute("Select itemPrice from Items where itemName = \'"+item_name+"\'").fetchone()[0]
        self.update_total(addedItemCost)

    def decrement_quantity(self, item_name):
        item_info = self.cart_items[item_name]
        if item_info['quantity'] > 1:
            item_info['quantity'] -= 1
            item_info['quantity_label'].text = str(item_info['quantity'])
        else:
            # Remove item from the cart if quantity reaches 0
            self.right_grid.remove_widget(item_info['quantity_label'].parent)
            del self.cart_items[item_name]
        deletedItemCost = self.cursor.execute("Select itemPrice from Items where itemName = \'"+item_name+"\'").fetchone()[0]
        self.update_total(-deletedItemCost)
    
    def update_total(self,price):
        print("Adding",price)
        self.total_price += price
        self.price_label.text = "Total Price : "+str(self.total_price)


    def _keyboard_closed(self):
        self.keyboard.unbind(on_key_down=self._on_keyboard_down)
        self.keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if text == None or keycode[1] == 'enter':
            # When Enter is pressed, process the barcode
            print(f"Barcode scanned: {self.barcode_buffer}")
            # You can call a function here to handle the barcode data
            self.process_barcode(self.barcode_buffer)
            self.barcode_buffer = ""  # Clear the buffer after processing
        else:
            # Add the character to the barcode buffer
            print(text)
            self.barcode_buffer += text

    def process_barcode(self,barcode):
        # Search for barcode match in the database
        barcodeMatch = self.cursor.execute("Select * from Items where itemCode = \'"+barcode+"\'").fetchall()
        if len(barcodeMatch) > 0:    
            barcodeMatch = barcodeMatch[0]        
            print("Scanned product is "+barcodeMatch[1])

            # Create a temporary Button instance to conveniently pass to add_to_cart, so as to not redefine the function
            temp_button = Button(text=barcodeMatch[1]+", MRP : "+str(barcodeMatch[2]), size_hint_y=None, height=40)
            self.add_to_cart(temp_button)
        else:
            print("Invalid Barcode")

if __name__ == '__main__':
    POSApp().run()
