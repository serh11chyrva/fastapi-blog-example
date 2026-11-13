import { Navigate, Route, Routes } from "react-router-dom";
import { usePageTitle } from "./usePageTitle";
import { ProtectedRoute } from "./ProtectedRoute";
import { SiteLayout } from "./layouts/SiteLayout";
import { ReadingLayout } from "./layouts/ReadingLayout";
import { FeedPage } from "../features/feed/FeedPage";
import { SearchPage } from "../features/search/SearchPage";
import { AuthPage } from "../features/auth/AuthPage";
import { ProfilePage } from "../features/profiles/ProfilePage";
import { ProfileSettingsPage } from "../features/profiles/ProfileSettingsPage";
import { SettingsLayout } from "../features/profiles/SettingsLayout";
import { MyArticlesPage } from "../features/articles/MyArticlesPage";
import { ArticlePage } from "../features/articles/ArticlePage";
import { SharedPublicationPage } from "../features/articles/SharedPublicationPage";
import { ArticleEditorPage } from "../features/articles/ArticleEditorPage";
import { SessionsPage } from "../features/profiles/sessions/SessionsPage";
import { SavedPage } from "../features/interactions/SavedPage";
import { NotificationsPage } from "../features/notifications/NotificationsPage";
import { PostPage } from "../features/feed/PostPage";
import { ThreadPage } from "../features/feed/ThreadPage";
import { LegalPage } from "../features/legal/LegalPage";
import { EmptyState } from "../shared/ui/EmptyState";
function NotFoundPage() {
  usePageTitle("Page not found");
  return <EmptyState title="Page not found" body="The page you are looking for does not exist." />;
}

export function AppRoutes() {
  return <Routes>
    <Route path="login" element={<AuthPage />} />
    <Route path="register" element={<AuthPage />} />


    <Route element={<SiteLayout />}>


      <Route index element={<FeedPage />} />
      <Route path="search" element={<SearchPage />} />
      <Route path="legal" element={<LegalPage />} />


      <Route path=":handle" element={<ProfilePage />} />

      <Route element={<ProtectedRoute />}>


        <Route path="following" element={<FeedPage following />} />

        <Route path="saved" element={<SavedPage />} />

        <Route path="notifications" element={<NotificationsPage />} />

        <Route path="my-articles" element={<MyArticlesPage />} />

        <Route path="settings" element={<SettingsLayout />}>
          <Route index element={<Navigate to="profile" replace />} />
          <Route path="profile" element={<ProfileSettingsPage />} />
          <Route path="sessions" element={<SessionsPage />} />
        </Route>

      </Route>

      <Route path="*" element={<NotFoundPage />} />

    </Route>

    <Route element={<ReadingLayout />}>


      <Route path="posts/:postId" element={<PostPage />} />
      <Route path="posts/:postId/thread" element={<ThreadPage />} />

      <Route path="articles/:articleId" element={<ArticlePage />} />

      <Route path=":handle/:shareSlug" element={<SharedPublicationPage />} />

      <Route element={<ProtectedRoute />}>


        <Route path="write" element={<ArticleEditorPage key="new" />} />

        <Route path="articles/:articleId/edit" element={<ArticleEditorPage />} />

      </Route>

    </Route>

  </Routes>;
}
