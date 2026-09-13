import requests

def get_working_proxies(max_working=3):
    """Fetches a list of free HTTP proxies from ProxyScrape and tests them."""
    all_proxies = get_free_proxies()
    working_proxies = test_proxies(all_proxies, max_working=max_working)
    return working_proxies

def get_free_proxies():
    """Fetches a list of free HTTP proxies from ProxyScrape."""
    print("Fetching proxy list...")
    # This API returns a plain text list of IPs and ports (IP:PORT)
    url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=yes&anonymity=all"
    response = requests.get(url)
    
    # Split the raw text by line breaks into a list
    proxies = response.text.strip().split('\r\n')
    print(f"Found {len(proxies)} total proxies.\n")
    return proxies

def test_proxies(proxy_list, max_working=3):
    """Tests proxies and returns a list of working ones."""
    working_proxies = []
    test_url = "https://httpbin.org/ip"
    
    print(f"Testing proxies (stopping after finding {max_working})...")
    
    for proxy in proxy_list:
        if len(working_proxies) >= max_working:
            break
            
        proxy_dict = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}"
        }
        
        try:
            # A strict 3-second timeout is critical. 
            # Free proxies are slow; if it takes longer, it's not worth using.
            response = requests.get(test_url, proxies=proxy_dict, timeout=3)
            
            if response.status_code == 200:
                print(f"[SUCCESS] {proxy} is working!")
                print(f"Server sees IP: {response.json()['origin']}")
                working_proxies.append(proxy_dict)
                
        except requests.exceptions.RequestException:
            # The proxy timed out, refused connection, or failed. Ignore and move on.
            print(f"[FAILED] {proxy}")
            
    return working_proxies

if __name__ == "__main__":
    # Run the fetch and test
    all_proxies = get_free_proxies()

    good_proxies = test_proxies(all_proxies)

    if good_proxies:
        print(f"proxies = {good_proxies[0]}")
    else:
        print("\nCould not find any working proxies in that batch. Try again later.")