use std::cmp;
use std::env;
use std::ffi::OsStr;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::SystemTime;

use clap;
use grep::cli;
use grep::matcher::LineTerminator;
#[cfg(feature = "pcre2")]
use grep::pcre2::{
    RegexMatcher as PCRE2RegexMatcher,
    RegexMatcherBuilder as PCRE2RegexMatcherBuilder,
};
use grep::printer::{
    ColorSpecs, Stats,
    JSON, JSONBuilder,
    Standard, StandardBuilder,
    Summary, SummaryBuilder, SummaryKind,
    default_color_specs,
};
use grep::regex::{
    RegexMatcher as RustRegexMatcher,
    RegexMatcherBuilder as RustRegexMatcherBuilder,
};
use grep::searcher::{
    BinaryDetection, Encoding, MmapChoice, Searcher, SearcherBuilder,
};
use ignore::overrides::{Override, OverrideBuilder};
use ignore::types::{FileTypeDef, Types, TypesBuilder};
use ignore::{Walk, WalkBuilder, WalkParallel};
use log;
use num_cpus;
use path_printer::{PathPrinter, PathPrinterBuilder};
use regex;
use termcolor::{
    WriteColor,
    BufferWriter, ColorChoice,
};

use app;
use config;
use logger::Logger;
use messages::{set_messages, set_ignore_messages};
use search::{PatternMatcher, Printer, SearchWorker, SearchWorkerBuilder};
use subject::SubjectBuilder;
use Result;

/// The command that ripgrep should execute based on the command line
/// configuration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Command {
    /// Search using exactly one thread.
    Search,
    /// Search using possibly many threads.
    SearchParallel,
    /// The command line parameters suggest that a search should occur, but
    /// ripgrep knows that a match can never be found (e.g., no given patterns
    /// or --max-count=0).
    SearchNever,
    /// Show the files that would be searched, but don't actually search them,
    /// and use exactly one thread.
    Files,
    /// Show the files that would be searched, but don't actually search them,
    /// and perform directory traversal using possibly many threads.
    FilesParallel,
    /// List all file type definitions configured, including the default file
    /// types and any additional file types added to the command line.
    Types,
}

impl Command {
    /// Returns true if and only if this command requires executing a search.
    fn is_search(&self) -> bool {
        use self::Command::*;

        match *self {
            Search | SearchParallel => true,
            SearchNever | Files | FilesParallel | Types => false,
        }
    }
}

/// The primary configuration object used throughout ripgrep. It provides a
/// high-level convenient interface to the provided command line arguments.
///
/// An `Args` object is cheap to clone and can be used from multiple threads
/// simultaneously.
#[derive(Clone, Debug)]
pub struct Args(Arc<ArgsImp>);

#[derive(Clone, Debug)]
struct ArgsImp {
    /// Mid-to-low level routines for extracting CLI arguments.
    matches: ArgMatches,
    /// The patterns provided at the command line and/or via the -f/--file
    /// flag. This may be empty.
    patterns: Vec<String>,
    /// A matcher built from the patterns.
    ///
    /// It's important that this is only built once, since building this goes
    /// through regex compilation and various types of analyses. That is, if
    /// you need many of theses (one per thread, for example), it is better to
    /// build it once and then clone it.
    matcher: PatternMatcher,
    /// The paths provided at the command line. This is guaranteed to be
    /// non-empty. (If no paths are provided, then a default path is created.)
    paths: Vec<PathBuf>,
    /// Returns true if and only if `paths` had to be populated with a single
    /// default path.
    using_default_path: bool,
}

impl Args {
    /// Parse the command line arguments for this process.
    ///
    /// If a CLI usage error occurred, then exit the process and print a usage
    /// or error message. Similarly, if the user requested the version of
    /// ripgrep, then print the version and exit.
    ///
    /// Also, initialize a global logger.
    pub fn parse() -> Result<Args> {
        // We parse the args given on CLI. This does not include args from
        // the config. We use the CLI args as an initial configuration while
        // trying to parse config files. If a config file exists and has
        // arguments, then we re-parse argv, otherwise we just use the matches
        // we have here.
        let early_matches = ArgMatches::new(app::app().get_matches());
        set_messages(!early_matches.is_present("no-messages"));
        set_ignore_messages(!early_matches.is_present("no-ignore-messages"));

        if let Err(err) = Logger::init() {
            return Err(format!("failed to initialize logger: {}", err).into());
        }
        if early_matches.is_present("trace") {
            log::set_max_level(log::LevelFilter::Trace);
        } else if early_matches.is_present("debug") {
            log::set_max_level(log::LevelFilter::Debug);
        } else {
            log::set_max_level(log::LevelFilter::Warn);
        }

        let matches = early_matches.reconfigure();
        // The logging level may have changed if we brought in additional
        // arguments from a configuration file, so recheck it and set the log
        // level as appropriate.
        if matches.is_present("trace") {
