import { BrowserRouter, Routes, Route } from "react-router-dom";
import LibraryPage from "./components/LibraryPage";
import MediaPage from "./components/MediaPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LibraryPage />} />
        <Route path="/media/:id" element={<MediaPage />} />
      </Routes>
    </BrowserRouter>
  );
}
