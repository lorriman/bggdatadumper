- [ ] Encoding error on Windows. Implement https://stackoverflow.com/questions/27092833/

- [ ] uncomment the main exception handler. Commented out for debugging.

- [x] refactor fetchxml and remove the processing code in to its own function

- [x] other random refactorings/rationalisations (processing code could be chopped up)

- [ ] rename functions and classes according to PEP 8 style guide, also ref google style guide

- [x] do docstrings properly

- [ ] more unittests (just the basics are tested)

- [ ] mock webserver for unittests (currently using http.server with some test html)

- [ ] move unittests to a modern system (pytest?)

- [ ] rejig to do proper stdout and stdin to make it pipeable

- [ ] security regexes to filter for common attacks (DDOS are the only ones left, so low priority)

- [ ] security: variable to max-depth recusion, avoid stack blow. (DDOS, low priority)

- [X] ~~change txt files to md~~
