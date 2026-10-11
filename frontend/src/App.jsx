import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import Dashboard from './pages/Dashboard'
import Products from './pages/Products'
import ProductProfile from './pages/ProductProfile'
import ProductForm from './pages/ProductForm'
import Imports from './pages/Imports'
import Duplicates from './pages/Duplicates'
import DuplicateDetails from './pages/DuplicateDetails'
import Reviews from './pages/Reviews'
import AuditTrail from './pages/AuditTrail'
import Categories from './pages/Categories'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/new" element={<ProductForm mode="add" />} />
          <Route path="/products/:id" element={<ProductProfile />} />
          <Route path="/products/:id/edit" element={<ProductForm mode="edit" />} />
          <Route path="/imports" element={<Imports />} />
          <Route path="/duplicates" element={<Duplicates />} />
          <Route path="/duplicates/:id" element={<DuplicateDetails />} />
          <Route path="/reviews" element={<Reviews />} />
          <Route path="/audit" element={<AuditTrail />} />
          <Route path="/categories" element={<Categories />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
