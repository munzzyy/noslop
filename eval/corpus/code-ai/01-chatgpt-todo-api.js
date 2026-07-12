// Import the necessary modules
const express = require('express');
const bodyParser = require('body-parser');

// Initialize the Express application
const app = express();
app.use(bodyParser.json());

// In-memory storage for our todos
let todos = [];
let nextId = 1;

// GET /todos - Retrieve all todos
app.get('/todos', (req, res) => {
  // Return the list of todos
  res.json(todos);
});

// GET /todos/:id - Retrieve a single todo by its ID
app.get('/todos/:id', (req, res) => {
  // First, we parse the ID from the request parameters
  const id = parseInt(req.params.id);
  // Then, we find the todo with the matching ID
  const todo = todos.find((item) => item.id === id);
  if (!todo) {
    // If the todo is not found, return a 404 error
    return res.status(404).json({ error: 'Todo not found' });
  }
  res.json(todo);
});

// POST /todos - Create a new todo
app.post('/todos', (req, res) => {
  try {
    // Extract the title from the request body
    const { title } = req.body;
    if (!title) {
      return res.status(400).json({ error: 'Title is required' });
    }
    // Create the new todo object
    const newTodo = {
      id: nextId++,
      title: title,
      completed: false,
    };
    // Add the new todo to our storage
    todos.push(newTodo);
    res.status(201).json(newTodo);
  } catch (error) {
    console.error('An error occurred:', error);
    res.status(500).json({ error: 'Something went wrong' });
  }
});

// DELETE /todos/:id - Delete a todo
app.delete('/todos/:id', (req, res) => {
  const id = parseInt(req.params.id);
  // Filter out the todo with the matching ID
  todos = todos.filter((item) => item.id !== id);
  res.status(204).send();
});

// Start the server on port 3000
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});

// Note: In a real application, you would use a database instead of
// in-memory storage. You can customize this as needed for your use case.
