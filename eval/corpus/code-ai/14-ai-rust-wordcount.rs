use std::collections::HashMap;
use std::env;
use std::fs;
use std::process;

/// Counts the occurrences of each word in a text file.
///
/// This program reads a file, splits it into words, and prints
/// the most frequent words in descending order.

fn main() {
    // Collect the command line arguments
    let args: Vec<String> = env::args().collect();

    // Check that a filename was provided
    if args.len() != 2 {
        eprintln!("Usage: {} <filename>", args[0]);
        process::exit(1);
    }

    // Read the contents of the file
    let contents = match fs::read_to_string(&args[1]) {
        Ok(text) => text,
        Err(e) => {
            eprintln!("An error occurred while reading the file: {}", e);
            process::exit(1);
        }
    };

    // Create a HashMap to store the word counts
    let mut word_counts: HashMap<String, u32> = HashMap::new();

    // Iterate over each word in the text
    for word in contents.split_whitespace() {
        // Normalize the word by converting to lowercase and removing punctuation
        let normalized: String = word
            .chars()
            .filter(|c| c.is_alphanumeric())
            .collect::<String>()
            .to_lowercase();

        // Skip empty strings after normalization
        if normalized.is_empty() {
            continue;
        }

        // Increment the count for this word
        *word_counts.entry(normalized).or_insert(0) += 1;
    }

    // Convert the HashMap into a vector so we can sort it
    let mut counts: Vec<(&String, &u32)> = word_counts.iter().collect();

    // Sort the vector by count in descending order
    counts.sort_by(|a, b| b.1.cmp(a.1));

    // Print the top 10 most frequent words
    println!("Top 10 most frequent words:");
    for (word, count) in counts.iter().take(10) {
        println!("{}: {}", word, count);
    }
}
