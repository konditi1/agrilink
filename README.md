# AgriLink - Farm-to-Table Marketplace Platform

## Overview

AgriLink is a comprehensive agricultural marketplace platform built with Django and Django REST Framework. It connects various stakeholders in the agricultural value chain - from seed producers to farmers to end consumers - creating an efficient ecosystem for agricultural commerce.

The platform facilitates direct connections between:
- Seed producers
- Seedling growers
- Farmers
- End consumers

## Features

### Core Functionality
- **User Authentication & Role Management**: Custom user models for different stakeholders
- **Product Management**: Comprehensive catalog with agricultural-specific attributes
- **Inventory Management**: Stock tracking and alerts
- **Order Processing**: Complete order lifecycle management
- **Multi-tier Supplier Connections**: Linking various actors in the agricultural value chain

### Additional Features
- **Category & Tag System**: Organize products by type, season, etc.
- **Search & Filtering**: Find products by various criteria
- **Image Management**: Multiple product images with primary image selection
- **Location-based Services**: Connect with local producers
- **Rating & Review System**: Build trust in the marketplace
- **Messaging System**: Facilitate communication between users

## Technology Stack

- **Backend**: Django, Django REST Framework
- **Database**: PostgreSQL (recommended)
- **Authentication**: JWT (JSON Web Tokens)
- **File Storage**: Django's default storage system
- **API**: RESTful API architecture