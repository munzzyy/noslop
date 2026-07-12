#include <iostream>

/**
 * A simple singly linked list implementation.
 * This class demonstrates the basic operations of a linked list.
 */

// Node structure representing each element in the list
struct Node {
    int data;
    Node* next;

    // Constructor to initialize the node
    Node(int value) : data(value), next(nullptr) {}
};

class LinkedList {
private:
    // Pointer to the first node in the list
    Node* head;
    // The number of elements in the list
    int size;

public:
    // Constructor to initialize an empty list
    LinkedList() : head(nullptr), size(0) {}

    // Destructor to free all allocated memory
    ~LinkedList() {
        // Iterate over the list and delete each node
        Node* current = head;
        while (current != nullptr) {
            Node* next = current->next;
            delete current;
            current = next;
        }
    }

    // Insert a new node at the beginning of the list
    void insertFront(int value) {
        // Create the new node
        Node* newNode = new Node(value);
        // Point the new node to the current head
        newNode->next = head;
        // Update the head to the new node
        head = newNode;
        size++;
    }

    // Remove the first occurrence of a value from the list
    bool remove(int value) {
        // Handle the case where the list is empty
        if (head == nullptr) {
            return false;
        }

        // Handle the case where the head contains the value
        if (head->data == value) {
            Node* temp = head;
            head = head->next;
            delete temp;
            size--;
            return true;
        }

        // Search for the value in the rest of the list
        Node* current = head;
        while (current->next != nullptr) {
            if (current->next->data == value) {
                Node* temp = current->next;
                current->next = temp->next;
                delete temp;
                size--;
                return true;
            }
            current = current->next;
        }

        // The value was not found in the list
        return false;
    }

    // Print all the elements in the list
    void print() const {
        Node* current = head;
        while (current != nullptr) {
            std::cout << current->data << " -> ";
            current = current->next;
        }
        std::cout << "nullptr" << std::endl;
    }
};

// Example usage of the LinkedList class
int main() {
    LinkedList list;

    // Insert some sample values
    list.insertFront(3);
    list.insertFront(2);
    list.insertFront(1);

    // Print the list contents
    list.print();

    // Remove a value and print again
    list.remove(2);
    list.print();

    return 0;
}
