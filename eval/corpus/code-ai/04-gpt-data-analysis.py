# Data Analysis Script for Sales Data
# This script loads sales data, performs analysis, and generates visualizations.

# Import necessary libraries
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Step 1: Load the dataset
# Replace with your actual file path
df = pd.read_csv("path/to/your/sales_data.csv")

# Step 2: Clean the data
# Remove any rows with missing values
df = df.dropna()

# Convert the date column to datetime format
df["date"] = pd.to_datetime(df["date"])

# Step 3: Calculate summary statistics
# Get the total sales for each product category
category_sales = df.groupby("category")["sales"].sum()
print("Total sales by category:")
print(category_sales)

# Calculate the average order value
average_order = df["sales"].mean()
print(f"Average order value: {average_order:.2f}")

# Step 4: Analyze monthly trends
# Group the sales by month
df["month"] = df["date"].dt.to_period("M")
monthly_sales = df.groupby("month")["sales"].sum()

# Step 5: Create the visualizations
# Create a bar chart of sales by category
plt.figure(figsize=(10, 6))
category_sales.plot(kind="bar", color="skyblue")
plt.title("Total Sales by Category")
plt.xlabel("Category")
plt.ylabel("Sales")
plt.tight_layout()
plt.savefig("sales_by_category.png")
print("Successfully saved the category chart! 📊")

# Create a line chart of monthly sales trends
plt.figure(figsize=(10, 6))
monthly_sales.plot(kind="line", marker="o", color="green")
plt.title("Monthly Sales Trend")
plt.xlabel("Month")
plt.ylabel("Sales")
plt.tight_layout()
plt.savefig("monthly_trend.png")
print("Successfully saved the trend chart! 📈")

# Finally, we print a summary of the analysis
print("Analysis complete. The results have been saved as PNG files.")
print("You can customize the charts as needed for your presentation.")
