Claude.md

Rules to follow:

This file provides guidance to Claude Code when working with code in this repository.

Create a new Branch at the beginning of this session.

Rules to Follow:

ALWAYS write secure best practice Python code.
Always try to write as lean as possible code. Don't blow up the repo. 4 Iterate function based on test results
MOVE Test scripts to the tests folder if they are not already there and ensure that they could be reused for later Tests for code coverage or reruns.
ALWAYS commit after each new function is added to our codebase
Ensure that you are using uv for isolating environments and packagemanagement
Use tree command for project structure.
Ensure that if you are finished with all issue a pull requests are created.
Create a tmp folder for development. And create a scratchpad.md file in this folder to chronologically document the development process.
Give the user after each finished step a short advise how to test your implementation. Write this in a test_advice.md file in the /tmp/ folder.
Always update or create the docs/usage.md file with the newly changed functionality to know how to use the actual implementation.
Absolut important keep the repo lean and clean, don't add unnecessary files, don't overengineer.

Use the Following Services:
Ollama: Base URL: host.docker.internal:11434
Postgres: psql -h localhost -U codeuser -d codeuser -c "SELECT version();" User: codeuser PW: devpassword
Redis: also localhost. redis-cli get test_key
