import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import '@fontsource-variable/atkinson-hyperlegible-next'          // the interface typeface (variable weight)
import '@fontsource-variable/atkinson-hyperlegible-next/wght-italic.css'   // margin notes are italic
import '@fontsource/tinos/400.css'                                // the essay typeface
import '@fontsource/tinos/700.css'
import './styles/tokens.css'
import './styles/base.css'
import App from './App.jsx'
import ComponentsSheet from './pages/ComponentsSheet.jsx'
import Placeholder from './pages/Placeholder.jsx'

createRoot(/** @type {HTMLElement} */ (document.getElementById('root'))).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<App />}>
          <Route index element={<Placeholder title="Did a student or an AI write this essay?" phase={4} />} />
          <Route path="fool" element={<Placeholder title="Try to fool it" phase={5} />} />
          <Route path="class" element={<Placeholder title="Check a class" phase={6} />} />
          <Route path="components" element={<ComponentsSheet />} />
          <Route path="*" element={<Placeholder title="There is no page here" phase="—" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
