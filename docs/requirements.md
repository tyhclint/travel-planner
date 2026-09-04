# FINAL PRODUCT
Our final product will be a travel application that based on user requirements, will be able to suggest a could of plans for the user
this will allow the user to customise their trip.

It will be a microservice architecture that is wired up to google maps, trip.com, as well as other apis


# MVP
The MVP will just be a simple langchain + MCP server that provides user with the plan, after a few rounds of querying
It will query some flights and hotels and make some suggestions, but for now it is a simple server that users can run with
their LLM agent. we will perhaps consider a vector store of data regarding different countries, or if let the user LLM query the internet.