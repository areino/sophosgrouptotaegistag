#!/usr/bin/env python3

import os
import sys
import time
import creds
import requests
import datetime
from time import sleep

def log(s):
    print(datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S") + '  ' + str(s))

def get_bearer_token_sophos(client_id: str, client_secret: str) -> str:
    """
    Exchange CLIENT_ID + CLIENT_SECRET for a short-lived bearer token
    using the OAuth 2.0 client_credentials grant.
    """
    response = requests.post(
        "https://id.sophos.com/api/v2/oauth2/token",
        data={
            "grant_type":    "client_credentials",
            "client_id":     client_id,
            "client_secret": client_secret,
            "scope": "token"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise ValueError(f"No access_token in auth response: {response.json()}")
    return token
    
    
def get_bearer_token_taegis(client_id: str, client_secret: str) -> str:
    """
    Exchange CLIENT_ID + CLIENT_SECRET for a short-lived bearer token
    using the OAuth 2.0 client_credentials grant.
    """
    response = requests.post(
        creds.taegis_api_endpoint + "/auth/api/v2/auth/token",
        json={
            "grant_type":    "client_credentials",
            "client_id":     client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise ValueError(f"No access_token in auth response: {response.json()}")
    return token

def get_sophos_tags(endpoint_id: str, tenant_id: str ) -> str:
    url = "https://api-" + creds.sophos_data_region + ".central.sophos.com/endpoint/v1/endpoints/" + endpoint_id
    error = ""
    
    try:
        resp = requests.get(
            url,
            headers={
                "Authorization": "Bearer " + token_sophos,
                "X-Tenant-ID": tenant_id,
                "Accept": "application/json",
            },
            timeout=10,
        )
        resp.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        error = "Connection error"
    except requests.exceptions.Timeout as e:
        error = "Timeout"
    except requests.exceptions.HTTPError as e:
        error = "HTTP error"
    except requests.exceptions.RequestException as e:
        error = "Eequest error"

    if len(error)>0:
        log("-- Host " + endpoint_id + " - " + error)
        return("")
    
    tags = resp.json().get("tags")      
  
    return(tags)


def get_sophos_group(endpoint_id: str, tenant_id: str ) -> str:
    url = "https://api-" + creds.sophos_data_region + ".central.sophos.com/endpoint/v1/endpoints/" + endpoint_id
    error = ""
    
    try:
        resp = requests.get(
            url,
            headers={
                "Authorization": "Bearer " + token_sophos,
                "X-Tenant-ID": tenant_id,
                "Accept": "application/json",
            },
            timeout=10,
        )
        resp.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        error = "Connection error"
    except requests.exceptions.Timeout as e:
        print(e)
        error = "Timeout"
    except requests.exceptions.HTTPError as e:
        error = "HTTP error"
    except requests.exceptions.RequestException as e:
        error = "Eequest error"

    if len(error)>0:
        log("-- Host " + endpoint_id + " - " + error)
        return("")
    
    group = resp.json().get("group")
    if group is None:
        groupname=""
        log("-- Host " + endpoint_id + " does not belong top any Sophos group")
    else:
        groupname = group["name"]
        log("-- Host " + endpoint_id + " belongs to Sophos group " + groupname)        
  
    return(groupname)

    

def run_graphql(token: str, query: str, variables: dict) -> dict:
    """
    POST a GraphQL query with the bearer token and tenant context header.
    Handles 429 rate-limit with a simple backoff retry.
    """
    headers = {
        "Authorization":  f"Bearer {token}",
        "X-Tenant-Context": creds.taegis_tenant_id,      # required for tenant-scoped calls
        "Content-Type":   "application/json",
    }

    resp = requests.post(
        creds.taegis_api_endpoint + "/graphql",
        json={"query": query, "variables": variables},
        headers=headers,
        timeout=30,
    )

    if resp.status_code == 429:
        log(f"[429] Rate limited. Retrying later.")
        exit()
        

    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(f"GraphQL errors: {payload['errors']}")

    return payload["data"]


def set_taegis_tag(asset: dict, hostid: str, tagname: str):
    
    ## check that tag is not already set
    tags = asset["tags"]
    for tag in tags:
        if tagname.lower() == tag["key"].lower():
            log("-- Skipped, already set - " + asset["hostnames"][0]["hostname"])
            return
    
    QUERY = """
        mutation CreateAssetTag($hostid: String!, $tagname: String!)  {
        createAssetTag(
            hostId: $hostid
            tag: $tagname
        ) {
            id
            hostId
            tag
            key
        }
    }
    
    """

    data = run_graphql(token_taegis, QUERY, variables={"hostid": hostid, "tagname": tagname})
    

def get_taegis_assets() -> dict:
    ## Get all Sophos endpoints from Taegis

    ASSET_SEARCH_QUERY = """
    query AssetsV2 {
        assetsV2(filter: { endpointTypes: [ENDPOINT_SOPHOS, ENDPOINT_SOPHOS_CIXA] }) {
            totalCount
            assets {
                id
                hostId
                hostnames {
                    hostname
                }
                tags {
                    tag
                    key
                    value
                }
                endpointType
            }
        }
    }
    """

    data = run_graphql(
        token_taegis,
        ASSET_SEARCH_QUERY,
        variables={}
    )

    result    = data.get("assetsV2", {})
    assets    = result.get("assets", [])
    total     = result.get("totalCount", "?")

    return(assets)
    
    


 
if __name__ == "__main__":

    log("Starting tagger process")
    
    log("Authenticating to Sophos...")
    token_sophos = get_bearer_token_sophos(creds.sophos_client_id, creds.sophos_client_secret)
 
    log("Authenticating to Taegis...")
    token_taegis = get_bearer_token_taegis(creds.taegis_client_id, creds.taegis_client_secret)
    
    log("Getting list of Taegis assets")
    assets = get_taegis_assets()
    log("-- Retrieved " + str(len(assets)) + " Sophos assets from Taegis")

    log("Getting tags for corresponding assets in Sophos Central")
    for asset in assets:
        ##sleep(1)
        tags = get_sophos_tags(asset["hostId"], creds.sophos_tenant_id ) 
        if len(tags)>0:
            log("-- Set tag [" + tags[0]["key"] + "] for asset " + asset["hostId"] + " - " + asset["hostnames"][0]["hostname"])
            set_taegis_tag(asset, asset["hostId"], tags[0]["key"])
        else:
            log("-- No tags defined for asset " + asset["hostId"] + " - " + asset["hostnames"][0]["hostname"])

    
    
    

