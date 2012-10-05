"""
the repo reccommender
"""
import requests

import repowalker
from repowalker import Repo

MAX_API_CALLS = 50


def get_user(username):
    USERS_URL = "https://api.github.com/users/%s"
    
    r = requests.get(USERS_URL % username)
    
    api_calls = 1
    return r.json, 1





def get_repos(username):
    
    REPOS_URL = "https://api.github.com/users/%s/repos"
    
    r = requests.get(REPOS_URL % username)

    api_calls = 1
    return [Repo.from_json(repo_object) for repo_object in r.json], api_calls
    


def get_language_distribution(username):
    """
    returns a distribtution of users language
    """
    users_repos, api_calls = get_repos(username)
    
    language_count = {}
    
    for repo in users_repos:
        language_count[repo.language] = language_count.get(repo.language, 0) + 1
        
    return language_count, api_calls
    
def get_repo_key_function(user_object):
    """
    besides language, each possible repo has 2 features right now:s
    - watcher count (a sign of popularity)
    - forker count (roughly)
    
    other features that I would like to work in are:
     - age
     - activity (last commit? commit frequency?)
     - number of contributors?
     - size (in terms of code)
    
    anyway, what this function does is:
        given a user_object, returns weighted sort function.
        what im trying to capture is that the way that i sort repos
        is going to be different for a given user.
        a user that forks a lot will prefer a repo with high forks
        a user that hasn't contributed to a project will prefer something with a lot of contributors
        a vertern github user maybe wants a new repo (or the opposite, or vice versa)
    
    but right now, its not going to use the userobject, instead returning a function that
    returns 10 * forkers + 3 * watchers. (arbitrarily)
    """
    
    def key_function(repo):
        return repo.forks * 10 + repo.watchers * 3

    return key_function
    
def repo_reccommender_by_language(username):
    """
    returns repos sorted by a function specific to the user
    """
    
    # get a BFS of 100 repos or all of their second-degree repos (rate-limiting ourselves along the way)

    # we have to get their language
    # ideally i would get all of their repos, then get the full byte distribution of all the repos,
    # but unfortunately that's a lot of calls.
    # better to just get a list of their repos (1 call)
    # and then make a whole number distribution.

    print "Geting user..."
    user_object, api_calls = get_user(username)

#    users_language_distribution, api_calls = get_language_distribution(username)
    
    # the bfs... using list() to turn it from un-sortable set to a list
    print "Getting nearby repos for user..."
    close_repos_set, api_calls = repowalker.do_bfs_from_username(username, 100, MAX_API_CALLS)
    
    close_repos = list(close_repos_set)
    
    # we need to sort them somehow
    repo_key_function = get_repo_key_function(user_object)
    
    # ok, now we sort them! possibly slow
    print "Sorting repos"
    sorted_repos = sorted(close_repos, key=repo_key_function, reverse=True)
    
    # lets go through and separate them by language
    language_sorted_repos_hash = {}
    for repo in sorted_repos:
        language_sorted_repos_hash.setdefault(repo.language, []).append(repo)
    
    # ok lets return that
    return language_sorted_repos_hash
    
    
def repo_reccommender():
    """
    gets a user as input from the user
    
    gets the users top languages
    
    gets the reccomended repos by language
    
    outputs information to the user
    """
    username = raw_input('Enter a username > ')
    
    language_sorted_repos = repo_reccommender_by_language(username)
    
    print "getting language distribution..."
    language_distribution, api_calls = get_language_distribution(username)
    
    top_languages = sorted(language_distribution.keys(), key=lambda l : language_distribution[l], reverse=True)[:3]
    
    print "Your top languages, with top up to 5 repo reccommendations are:"
    
    for i, l in enumerate(top_languages):
        print "%d : %s" % (i, l)
        for repo in language_sorted_repos[l][:5]:
            print "\t%s" % str(repo)
        
    

    
    
if __name__ == "__main__":
    repo_reccommender()

    
    
    

