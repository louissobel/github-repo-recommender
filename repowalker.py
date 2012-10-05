"""
MOdule for finding a bunch of github repo names through a random walk
"""
import random
import requests


# datastructure for a repo is ('user', 'reposlug') pair
BASE_REPO = ('django', 'django')
FALLBACK_REPO = BASE_REPO

BASE_USER = 'louissobel'

# so we get the watchers of a repo.
# then we pick one of them randomly, and get the list of repos that they watch


# we hold on to some amount of users (lets cap it at say, N), ????? maybe
# so that if we ever come to a dead end we can backtrack.


# i gotta watch my rate limit

class Repo:
    
    @classmethod
    def from_json(cls, repo_object):
        return cls(
            repo_object['owner']['login'],
            repo_object['name'],
            repo_object['watchers'],
            repo_object['forks'],
            repo_object['language'],
        )
    
    
    def __init__(self, user, name, watchers, forks, language):
        self.user = user
        self.name = name
        self.watchers = watchers
        self.forks = forks
        self.language = language
        
    def __str__(self):
        return "%s/%s" % (self.user, self.name)
        
    def __repr__(self):
        return "<%s w:%d f:%d l:%s>" % (str(self), self.watchers, self.forks, self.language)
        
    def __hash__(self):
        return str(self).__hash__()
        
    def __eq__(self, other):
        return str(self) == str(other)
        


def apicalltrack(howmany):
    
    def decorator(function):
        function.api_calls = howmany
        return function
        
    return decorator

@apicalltrack(1)
def get_stargazers(repo):
    """
    returns a list of usernames that starred the repo with (user, reposlug) given
    """
    STARGAZERS_URL = "https://api.github.com/repos/%s/stargazers"
    
    r = requests.get(STARGAZERS_URL % str(repo))
    
    api_calls = 1
    return [user_object['login'] for user_object in r.json], api_calls
   
def get_starred_repos(username):
    """
    returns a list of repos that the given username has starred
    """
    STARGAZING_URL = "https://api.github.com/users/%s/starred"
    
    r = requests.get(STARGAZING_URL % username)
    
    api_calls = 1
    return [Repo.from_json(repo_object) for repo_object in r.json], api_calls

def get_neighbors(repo):
    """
    gets the set of repos that are connected to a repo by a follower in common
    """
    neighbor_set = set()
    api_call_count = 0
    
    stargazers, api_calls = get_stargazers(repo) #due to pagination, this will never be too high
    api_call_count += api_calls
    
    print "stargazers for %s: %s" % (str(repo), str(stargazers))
    
    for stargazer in stargazers:
         print "getting %s wathced repos" % stargazer
         stargazers_watched_repos, api_calls = get_starred_repos(stargazer)
         api_call_count += api_calls
         for repo in stargazers_watched_repos:
             neighbor_set.add(repo)
        
    
    return neighbor_set, api_call_count

def do_random_walk_from_repo(repo, target_repo_count, max_api_calls, repo_set=None):
    """
    will attempt to get target_repo_count repos by walking
    around githubs graph.
    
    will short-circuit if more than max_api_calls take place
    """
    if repo_set is None:
        repo_set = set()
    
    current_repo = repo
    
    api_call_count = 0
    
    while len(repo_set) < target_repo_count and api_call_count < max_api_calls:

        #print "Getting stargazers for %s" % str(current_repo)
        repo_stargazers, api_calls = get_stargazers(current_repo)
        
        # pick random stargazer
        random.shuffle(repo_stargazers)
        found_repo = None
        
        while not found_repo and repo_stargazers:
            chosen_one = repo_stargazers.pop()
            # get their starred repos
            #print "Getting starred repos for %s" % chosen_one
            his_starred_repos, api_calls = get_starred_repos(chosen_one)
        
            # now we have to randomally go through his_starred_repos
            random.shuffle(his_starred_repos)
            next_repo = his_starred_repos.pop() # we know it is at least one, so this is safe
            next_is_new = next_repo not in repo_set

            while not next_is_new and his_starred_repos:
                next_repo = his_starred_repos.pop()
                next_is_new = next_repo not in repo_set
            
            if next_is_new:
                found_repo = next_repo
        
        if found_repo:
            repo_set.add(found_repo)
            current_repo = found_repo
            
        else:
            print "Dead end, found %d repos using %d api_calls" % (len(repo_set), api_call_count)
            return repo_set, api_call_count
            
    print "Found %d repos using %d api calls." % (len(repo_set), api_call_count)
    return repo_set, api_call_count


def do_bfs_from_username(username, target_repo_count, max_api_calls):
    """
    will get repos that are 1, 2 degrees connected to this user
    """
    api_call_count = 0
    
    users_starred_repos, api_calls = get_starred_repos(username)
    api_call_count += api_calls
    
    print users_starred_repos
    
    # we have to filter out the ones that are the users
    users_starred_repos = [repo for repo in users_starred_repos if not repo.user==username]
    #I want to do bfs through it
    
    repo_set = set()
    
    frontier = users_starred_repos
    
    print "initial frontier: %s" % str(frontier)
    
    # we want to make sure we go through all of the initial frontier?
    # yes, but still bounded by our api_call constraint
    initial_frontier_length = len(frontier)
    
    iteration_count = 0
    while (len(repo_set) < target_repo_count or iteration_count < initial_frontier_length) and api_call_count < max_api_calls:
        iteration_count += 1
        
        if frontier:
            check_repo = frontier.pop(0)
            
            print "getting neighbors for %s" % str(check_repo)
            check_repo_neighbors, api_calls = get_neighbors(check_repo)
            api_call_count += api_calls
            for repo in check_repo_neighbors:
                if repo.user != username: # we don't want to go back to ourselves
                    if repo not in repo_set:
                        repo_set.add(repo)
                        frontier.append(repo) # put in on the back for BFS
                        
        else:
            # we've run out of places to check, but we still need some want more repos
            # and have more API calls to spend! so lets do random walk from django
            repo_set, api_calls = do_random_walk_from_repo(
                                    FALLBACK_REPO,
                                    target_repo_count - len(repo_set),
                                    max_api_calls - api_call_count,
                                    repo_set
                                  )
            api_call_count += api_calls
    
    # ok,,, so we've done as much as we can
    return repo_set, api_call_count
        
        
    
    

if __name__ == "__main__":
    repos, api_calls = do_bfs_from_username(BASE_USER, 10, 100)
    
    print "using bfs from %s found %d repos using %d api calls" % (BASE_USER, len(repos), api_calls)
    
    for repo in repos:
        print repr(repo)
    