import java.util.ArrayList;
import java.util.List;

/**
 * A simple inventory management system for tracking products.
 * This class provides methods to add, remove, and search for products.
 */
public class InventoryManager {

    // The list that stores all products in the inventory
    private List<Product> products;

    /**
     * Constructor to initialize the inventory manager.
     */
    public InventoryManager() {
        // Initialize the products list
        this.products = new ArrayList<>();
    }

    /**
     * Adds a product to the inventory.
     *
     * @param product The product to add.
     */
    public void addProduct(Product product) {
        // Add the product to the list
        products.add(product);
        System.out.println("Product added successfully: " + product.getName());
    }

    /**
     * Removes a product from the inventory by its ID.
     *
     * @param productId The ID of the product to remove.
     * @return true if the product was removed, false otherwise.
     */
    public boolean removeProduct(int productId) {
        // Iterate over the products to find the matching ID
        for (Product product : products) {
            if (product.getId() == productId) {
                products.remove(product);
                return true;
            }
        }
        // If we reach here, the product was not found
        return false;
    }

    /**
     * Searches for a product by its name.
     *
     * @param name The name of the product to search for.
     * @return The product if found, null otherwise.
     */
    public Product findProductByName(String name) {
        // Loop through the products list
        for (Product product : products) {
            // Check if the product name matches
            if (product.getName().equalsIgnoreCase(name)) {
                return product;
            }
        }
        return null;
    }

    /**
     * Calculates the total value of the inventory.
     *
     * @return The total value of all products.
     */
    public double getTotalValue() {
        double total = 0;
        // Sum up the price of each product multiplied by its quantity
        for (Product product : products) {
            total += product.getPrice() * product.getQuantity();
        }
        return total;
    }

    /**
     * Main method to demonstrate the inventory manager.
     */
    public static void main(String[] args) {
        // Create a new inventory manager instance
        InventoryManager manager = new InventoryManager();

        // Example usage: add some sample products
        manager.addProduct(new Product(1, "Laptop", 999.99, 5));
        manager.addProduct(new Product(2, "Mouse", 24.99, 20));

        // Print the total inventory value
        System.out.println("Total inventory value: " + manager.getTotalValue());
    }
}
