import React, { useState, useEffect } from 'react';

// Define the interface for our user data
interface User {
  id: number;
  name: string;
  email: string;
  isActive: boolean;
}

/**
 * UserDashboard component displays a list of users with filtering capabilities.
 */
const UserDashboard: React.FC = () => {
  // State to store the list of users
  const [users, setUsers] = useState<User[]>([]);
  // State to track the loading status
  const [loading, setLoading] = useState<boolean>(true);
  // State to store any error messages
  const [error, setError] = useState<string | null>(null);
  // State for the search filter
  const [searchTerm, setSearchTerm] = useState<string>('');

  // Fetch the users when the component mounts
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        // Fetch the user data from the API
        const response = await fetch('/api/users');
        if (!response.ok) {
          throw new Error('Failed to fetch users');
        }
        const data = await response.json();
        // Update the users state with the fetched data
        setUsers(data);
      } catch (err) {
        // Handle any errors that occurred during the fetch
        setError('An error occurred while loading users.');
        console.error('Error fetching users:', err);
      } finally {
        // Set loading to false regardless of the outcome
        setLoading(false);
      }
    };

    fetchUsers();
  }, []);

  // Filter the users based on the search term
  const filteredUsers = users.filter((user) =>
    user.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Show a loading indicator while the data is being fetched
  if (loading) {
    return <div className="loading">Loading users... ⏳</div>;
  }

  // Show an error message if something went wrong
  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div className="dashboard">
      <h1>User Dashboard 👥</h1>
      {/* Search input for filtering users */}
      <input
        type="text"
        placeholder="Search users..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
      />
      {/* Render the list of filtered users */}
      <ul className="user-list">
        {filteredUsers.map((user) => (
          <li key={user.id} className={user.isActive ? 'active' : 'inactive'}>
            <span>{user.name}</span>
            <span>{user.email}</span>
            <span>{user.isActive ? '✅ Active' : '❌ Inactive'}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default UserDashboard;
