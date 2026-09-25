import React from 'react';
import ModelRegistrationForm from '../components/ModelRegistrationForm';

export default function Register({ initialData }) {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-extrabold text-gray-900">
          {initialData?.model_name ? `Register New Version for ${initialData.model_name}` : 'Register Model'}
        </h1>
        <p className="text-gray-500 mt-2">
          {initialData?.model_name 
            ? `Uploading a new version to existing identity "${initialData.model_name}".`
            : 'Enter the details to register a new model or version.'}
        </p>
      </div>
      <ModelRegistrationForm initialData={initialData} />
    </div>
  );
}

