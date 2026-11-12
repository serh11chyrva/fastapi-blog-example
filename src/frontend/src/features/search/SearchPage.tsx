import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { usePageTitle } from "../../app/usePageTitle";
import type { SearchPublicationHit, SearchUser } from "../../shared/api/types";
import { HashtagText } from "../../shared/text/HashtagText";
import { Avatar } from "../../shared/ui/Avatar";
import { Icon } from "../../shared/ui/Icon";
import { InfiniteScroll } from "../../shared/ui/InfiniteScroll";
import { PeopleSkeleton } from "../../shared/ui/PeopleSkeleton";
import { PublicationListSkeleton } from "../publications/PublicationSkeleton";
import { publicationEvent, publicationStateEvent } from "../interactions/events";
import { FeedCard } from "../feed/FeedCard";
import { useSearchResults } from "./useSearchResults";
import "./search.css";

const userIdentity = (user: SearchUser) => user.id;
const publicationIdentity = (hit: SearchPublicationHit) => `${hit.publication.kind}:${hit.publication.id}`;

function UsersResults({ query }: { query: string }) {
  const [expanded, setExpanded] = useState(false);
  const results = useSearchResults<SearchUser>(`/search/users?${new URLSearchParams({ q: query })}`, 3, 10, userIdentity);
  return <section className="search-users" aria-labelledby="search-users-heading">
    <h2 id="search-users-heading">People</h2>
    {!results.loading && !results.error && !results.items.length && <p>No people found.</p>}
    <ul aria-busy={results.loading}>{(expanded ? results.items : results.items.slice(0, 3)).map((person) => <li key={person.id} className="search-person motion-enter">
      <Link to={`/@${person.username}`} aria-label={`${person.display_name}'s profile`}>
        <Avatar src={person.avatars.original} name={person.display_name} size="sm" />
      </Link>
      <div><strong><HashtagText text={person.display_name} href={`/@${person.username}`} /></strong>
        <Link className="search-person-handle" to={`/@${person.username}`}>@{person.username}</Link>
        {person.bio && <p><HashtagText text={person.bio} /></p>}
      </div>
    </li>)}</ul>
    {results.loading && !results.error && <PeopleSkeleton count={results.items.length ? 2 : 3}
      label="Searching people…" withBio />}
    {results.error && <p className="notice-error" role="alert">{results.error}{" "}
      <button type="button" className="text-link" onClick={() => void results.retry()}>Retry</button>
    </p>}
    {(results.cursor || !expanded && results.items.length > 3) && <button type="button" className="text-link"
      disabled={results.loading} onClick={() => {
        setExpanded(true);
        if (expanded || results.items.length <= 3) void results.loadMore();
      }}>{results.loading ? "Loading people…" : "Show more"}</button>}
    {expanded && <button type="button" className="text-link search-show-less" onClick={() => setExpanded(false)}>Show less</button>}
  </section>;
}

function PublicationResults({ query, sort }: { query: string; sort: string }) {
  const results = useSearchResults<SearchPublicationHit>(
    `/search/publications?${new URLSearchParams({ q: query, sort })}`, 20, 20, publicationIdentity,
  );
  useEffect(() => {
    window.addEventListener(publicationEvent, results.refresh);
    window.addEventListener(publicationStateEvent, results.refresh);
    return () => {
      window.removeEventListener(publicationEvent, results.refresh);
      window.removeEventListener(publicationStateEvent, results.refresh);
    };
  }, [results.refresh]);
  return <section className="search-publications" aria-labelledby="search-publications-heading">
    <h2 id="search-publications-heading" className="search-section-heading">Publications</h2>
    {results.error && <p className="notice-error search-section-heading" role="alert">{results.error}{" "}
      <button type="button" className="text-link" onClick={() => void results.retry()}>Retry</button>
    </p>}
    {!results.loading && !results.error && !results.items.length && <p className="list-status">No publications found.</p>}
    <div aria-busy={results.loading}>
      {results.items.map((hit) => <FeedCard key={publicationIdentity(hit)} item={hit.publication}
        excerpt={hit.excerpt} onChanged={results.refresh} />)}
    </div>
    {results.loading && !results.error && <PublicationListSkeleton count={results.items.length || results.cursor ? 2 : 3}
      label="Searching publications…" />}
    <InfiniteScroll hasMore={!!results.cursor} loading={results.loading} error={results.error} loadMore={results.loadMore} />
  </section>;
}

export function SearchPage() {
  usePageTitle("Search");
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const sort = params.get("sort") === "latest" ? "latest" : "relevance";
  const [input, setInput] = useState(query);
  useEffect(() => { setInput(query); }, [query]);
  useEffect(() => {
    if (input.trim() === query) return;
    const timer = window.setTimeout(() => {
      setParams((previous) => {
        const next = new URLSearchParams(previous);
        if (input.trim()) next.set("q", input.trim()); else next.delete("q");
        if (!next.has("sort")) next.set("sort", "relevance");
        return next;
      }, { replace: true });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [input, query, setParams]);
  const ready = [...query.trim()].length >= 2;
  return <section className="feed-list search-page" aria-label="Search">
    <header className="search-heading"><h1>Search</h1>
      <form className="search-form" role="search" onSubmit={(event) => {
        event.preventDefault();
        setParams({ ...(input.trim() ? { q: input.trim() } : {}), sort });
      }}>
        <Icon name="search" />
        <input type="search" aria-label="Search people and publications" placeholder="Search people, publications, or #hashtags"
          value={input} maxLength={200} onChange={(event) => setInput(event.target.value)} />
        <button type="submit" className="button-secondary">Search</button>
      </form>
      <label className="search-sort">Sort publications
        <select className="feed-filter" value={sort} onChange={(event) => setParams({ q: query, sort: event.target.value })}>
          <option value="relevance">Relevance</option><option value="latest">Latest</option>
        </select>
      </label>
    </header>
    {ready ? <><UsersResults key={query} query={query} /><PublicationResults query={query} sort={sort} /></>
      : <p className="list-status">Enter at least two characters or a #hashtag to find people and publications.</p>}
  </section>;
}
