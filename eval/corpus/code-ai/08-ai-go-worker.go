package main

// Import the necessary packages
import (
	"fmt"
	"sync"
	"time"
)

// Job represents a unit of work to be processed
type Job struct {
	ID      int
	Payload string
}

// Result represents the outcome of processing a job
type Result struct {
	JobID  int
	Output string
}

// worker processes jobs from the jobs channel and sends results to the results channel
func worker(id int, jobs <-chan Job, results chan<- Result, wg *sync.WaitGroup) {
	// Make sure to signal completion when the worker exits
	defer wg.Done()

	// Process each job from the channel
	for job := range jobs {
		// Simulate some processing time
		time.Sleep(100 * time.Millisecond)

		// Create the result for this job
		result := Result{
			JobID:  job.ID,
			Output: fmt.Sprintf("Processed payload: %s", job.Payload),
		}

		// Send the result to the results channel
		results <- result
	}
}

func main() {
	// Define the number of workers and jobs
	numWorkers := 3
	numJobs := 10

	// Create the channels for jobs and results
	jobs := make(chan Job, numJobs)
	results := make(chan Result, numJobs)

	// Create a WaitGroup to wait for all workers to finish
	var wg sync.WaitGroup

	// Step 1: Start the worker goroutines
	for i := 1; i <= numWorkers; i++ {
		wg.Add(1)
		go worker(i, jobs, results, &wg)
	}

	// Step 2: Send the jobs to the jobs channel
	for j := 1; j <= numJobs; j++ {
		jobs <- Job{ID: j, Payload: fmt.Sprintf("job-%d", j)}
	}
	// Close the jobs channel to signal that no more jobs will be sent
	close(jobs)

	// Step 3: Wait for all workers to complete
	wg.Wait()
	close(results)

	// Finally, we collect and print all the results
	for result := range results {
		fmt.Println(result.Output)
	}

	fmt.Println("All jobs have been processed successfully! ✅")
}
