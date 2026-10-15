import { Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./ProtectedRoute";
import { SiteLayout } from "./layouts/SiteLayout";
import { ReadingLayout } from "./layouts/ReadingLayout";
import { FeedPage } from "../features/feed/FeedPage";
import { AuthPage } from "../features/auth/AuthPage";
import { ProfilePage } from "../features/profiles/ProfilePage";
import { ProfileSettingsPage } from "../features/profiles/ProfileSettingsPage";
import { MyArticlesPage } from "../features/articles/MyArticlesPage";
import { ArticlePage } from "../features/articles/ArticlePage";
import { SharedPublicationPage } from "../features/articles/SharedPublicationPage";
import { ArticleEditorPage } from "../features/articles/ArticleEditorPage";
import { SessionsPage } from "../features/profiles/sessions/SessionsPage";
import { EmptyState } from "../shared/ui/EmptyState";
export function AppRoutes() {
  return <Routes>


    <Route element={<SiteLayout />}>


      <Route index element={<FeedPage />} />

      <Route path="login" element={<AuthPage />} />

      <Route path="register" element={<AuthPage />} />

      <Route path=":handle" element={<ProfilePage />} />

      <Route element={<ProtectedRoute />}>


        <Route path="following" element={<FeedPage following />} />

        <Route path="my-articles" element={<MyArticlesPage />} />

        <Route path="settings/profile" element={<ProfileSettingsPage />} />

        <Route path="settings/sessions" element={<SessionsPage />} />

      </Route>

      <Route path="*" element={<EmptyState title="Page not found" body="The page you are looking for does not exist." />} />

    </Route>

    <Route element={<ReadingLayout />}>


      <Route path="articles/:articleId" element={<ArticlePage />} />

      <Route path=":handle/:shareSlug" element={<SharedPublicationPage />} />

      <Route element={<ProtectedRoute />}>


        <Route path="write" element={<ArticleEditorPage key="new" />} />

        <Route path="articles/:articleId/edit" element={<ArticleEditorPage />} />

      </Route>

    </Route>

  </Routes>;
}
