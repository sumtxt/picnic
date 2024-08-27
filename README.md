When forking the repository, you need to make some changes to the repository settings:

1. Go to Settings > Actions > General. Scroll down to Workflow permissions and set allow workflows read and write permissions. 

2. Go to Security > Secrets and Variables > Actions. Set CROSSREF_EMAIL in as a repository secret. This email will be used to authenticate with the Crossref API. Read more [here](https://github.com/CrossRef/rest-api-doc#good-manners--more-reliable-service). 
