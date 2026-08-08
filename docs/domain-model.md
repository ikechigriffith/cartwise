# Domain Model

This is the first-pass data model for the grocery shopping optimization product. It reflects the language in `CONTEXT.md` and should evolve as domain decisions are refined.

## User

Represents a person who owns grocery lists and chooses fulfillment preferences.

Fields:
- `id`
- `email`
- `displayName`
- `defaultStartLocation`
- `defaultRadius`
- `defaultTransitMode` — `car` or `public_transit`
- `substitutionPreferences` — global defaults
- `createdAt`
- `updatedAt`

## GroceryList

A persistent collection of grocery items owned by a user.

Fields:
- `id`
- `userId`
- `name`
- `status` — draft, active, archived
- `items`
- `lastUsedAt`
- `createdAt`
- `updatedAt`

## GroceryListItem

An item the user wants to buy, expressed as a product family plus needed amount and constraints.

Fields:
- `id`
- `groceryListId`
- `productFamilyId`
- `neededAmount`
- `unit`
- `packageFlexibility`
- `requirements`
- `preferences`
- `substitutionOverrides`
- `notes`
- `createdAt`
- `updatedAt`

## ProductFamily

The general product intent a user may ask for, such as 2% milk or sandwich bread.

Fields:
- `id`
- `name`
- `categoryId`
- `subcategoryId`
- `commonAliases`
- `defaultUnit`
- `createdAt`
- `updatedAt`

## CanonicalProduct

The app's clean representation of an exact comparable grocery product across stores.

Fields:
- `id`
- `productFamilyId`
- `canonicalName`
- `brand`
- `isStoreBrand`
- `owningRetailerId` — only for store brands
- `barcode`
- `categoryId`
- `subcategoryId`
- `sizeValue`
- `sizeUnit`
- `packageQuantity`
- `tags`
- `requirementsSupported`
- `isPerishable`
- `createdAt`
- `updatedAt`

## ProductListing

A store-specific representation of a product.

Fields:
- `id`
- `storeId`
- `retailerProductId`
- `rawName`
- `rawDescription`
- `rawBrand`
- `price`
- `currency`
- `pricePerUnit`
- `packageQuantity`
- `unitSizeValue`
- `unitSizeUnit`
- `totalSizeValue`
- `totalSizeUnit`
- `normalizedSizeValue`
- `normalizedSizeUnit`
- `computedPricePerUnit`
- `computedPriceUnit`
- `unitPriceConfidence`
- `unitPriceNeedsReview`
- `stockAvailability`
- `source`
- `sourceUrl`
- `priceCheckedAt`
- `stockCheckedAt`
- `createdAt`
- `updatedAt`

## ProductMapping

The relationship between a product listing and a canonical product.

Fields:
- `id`
- `productListingId`
- `canonicalProductId`
- `confidence`
- `confidenceLevel` — high, medium, low
- `mappingMethod` — barcode, deterministic, semantic, manual
- `status` — approved, pending_review, rejected
- `reviewedBy`
- `reviewedAt`
- `createdAt`
- `updatedAt`

## Retailer

A grocery business or brand that may operate stores and expose shared integration surfaces.

Fields:
- `id`
- `name`
- `websiteUrl`
- `integrationType` — api, scrape, manual, partner
- `loyaltyProgramSupported`
- `createdAt`
- `updatedAt`

## RetailerDataSource

A source that may provide retailer product, price, stock, or store data.

Fields:
- `id`
- `retailerId`
- `sourceUrl`
- `sourceType` — website, api, scrape, manual, partner
- `hasProductCatalog`
- `hasPrices`
- `hasStock`
- `requiresLogin`
- `scrapeStatus` — candidate_strong, candidate_likely, needs_verification, active, blocked, retired
- `confidence` — high, medium, low, unknown
- `lastCheckedAt`
- `notes`
- `createdAt`
- `updatedAt`

## Store

A physical retail location operated by a retailer.

Fields:
- `id`
- `retailerId`
- `name`
- `storeType` — supermarket, convenience, specialty
- `address`
- `latitude`
- `longitude`
- `contactInfo`
- `serviceCapabilities` — delivery, pickup, in_store
- `storeHours`
- `transitAccessibility`
- `externalSource`
- `externalId`
- `rawTags`
- `isActive`
- `lastSeenAt`
- `sourceUpdatedAt`
- `needsReview`
- `verifiedAt`
- `createdAt`
- `updatedAt`

## ServiceAvailability

Whether a store capability is available for a specific user, time, or location.

Fields:
- `id`
- `storeId`
- `serviceCapability`
- `available`
- `availableFrom`
- `availableUntil`
- `checkedAt`
- `reasonUnavailable`

## ProposedPlan

An app-generated plan for fulfilling a grocery list.

Fields:
- `id`
- `groceryListId`
- `userId`
- `fulfillmentMethod` — guided or outsourced
- `primaryRecommendationId`
- `plannedStartTime`
- `startLocation`
- `endLocation`
- `radius`
- `transitMode`
- `metrics`
- `freshnessLabels`
- `createdAt`
- `expiresAt`

## PlanAlternative

A non-primary plan optimized for a specific trade-off.

Fields:
- `id`
- `proposedPlanId`
- `type` — best_balance, cheapest, fastest, fewest_stops
- `stops`
- `route`
- `itemAssignments`
- `metrics`
- `usesUncertainOverrides`
- `confidenceNotes`

## Stop

A store visit within a proposed plan.

Fields:
- `id`
- `planAlternativeId`
- `storeId`
- `sequence`
- `estimatedArrivalTime`
- `estimatedDepartureTime`
- `storeOpenAtArrival`
- `subtotal`

## ItemAssignment

The assignment of a grocery list item to a specific stop.

Fields:
- `id`
- `stopId`
- `groceryListItemId`
- `canonicalProductId`
- `productListingId`
- `assignedQuantity`
- `unit`
- `estimatedPrice`
- `pricePerUnit`
- `substitutionUsed`
- `requirementsSatisfied`
- `preferencesHonored`
- `freshnessLabel`
- `confidenceNotes`

## PlanMetrics

Estimated values used to explain a proposed plan.

Fields:
- `grocerySubtotal`
- `travelCost`
- `totalEstimatedCost`
- `estimatedTravelTime`
- `estimatedShoppingTime`
- `totalEstimatedTime`
- `numberOfStops`
- `estimatedSavings`
- `dataFreshnessSummary`
