/* tslint:disable */
/* eslint-disable */
/**
* @param {string} input
* @returns {string}
*/
export function generateUnsignedCredential(input: string): string;
/**
* @param {any} signatures
* @param {string} unsigned_info
* @param {bigint} expiry
* @returns {string}
*/
export function getDeploymentDetails(signatures: any, unsigned_info: string, expiry: bigint): string;
/**
* @param {any} signatures
* @param {string} unsigned_info
* @returns {string}
*/
export function getDeploymentInfo(signatures: any, unsigned_info: string): string;
/**
* @param {string} input
* @returns {string}
*/
export function createIdRequestV1(input: string): string;
/**
* @param {string} input
* @returns {string}
*/
export function createIdentityRecoveryRequest(input: string): string;
/**
* @param {string} raw_input
* @returns {string}
*/
export function createCredentialV1(raw_input: string): string;
/**
* @param {string} input
* @returns {string}
*/
export function createUnsignedCredentialV1(input: string): string;
/**
* @param {string} raw_input
* @returns {string}
*/
export function createIdProof(raw_input: string): string;
/**
* @param {string} seed_as_hex
* @param {string} raw_net
* @param {number} identity_provider_index
* @param {number} identity_index
* @param {number} credential_counter
* @returns {string}
*/
export function getAccountSigningKey(seed_as_hex: string, raw_net: string, identity_provider_index: number, identity_index: number, credential_counter: number): string;
/**
* @param {string} seed_as_hex
* @param {string} raw_net
* @param {number} identity_provider_index
* @param {number} identity_index
* @param {number} credential_counter
* @returns {string}
*/
export function getAccountPublicKey(seed_as_hex: string, raw_net: string, identity_provider_index: number, identity_index: number, credential_counter: number): string;
/**
* @param {string} serialized
* @returns {string}
*/
export function deserializeCredentialDeployment(serialized: string): string;
/**
* @param {string} seed_as_hex
* @param {string} raw_net
* @param {number} identity_provider_index
* @param {number} identity_index
* @param {number} credential_counter
* @param {string} raw_on_chain_commitment_key
* @returns {string}
*/
export function getCredentialId(seed_as_hex: string, raw_net: string, identity_provider_index: number, identity_index: number, credential_counter: number, raw_on_chain_commitment_key: string): string;
/**
* @param {string} seed_as_hex
* @param {string} raw_net
* @param {number} identity_provider_index
* @param {number} identity_index
* @returns {string}
*/
export function getPrfKey(seed_as_hex: string, raw_net: string, identity_provider_index: number, identity_index: number): string;
/**
* @param {string} seed_as_hex
* @param {string} raw_net
* @param {number} identity_provider_index
* @param {number} identity_index
* @returns {string}
*/
export function getIdCredSec(seed_as_hex: string, raw_net: string, identity_provider_index: number, identity_index: number): string;
/**
* @param {string} seed_as_hex
* @param {string} raw_net
* @param {number} identity_provider_index
* @param {number} identity_index
* @returns {string}
*/
export function getSignatureBlindingRandomness(seed_as_hex: string, raw_net: string, identity_provider_index: number, identity_index: number): string;
/**
* @param {string} seed_as_hex
* @param {string} raw_net
* @param {number} identity_provider_index
* @param {number} identity_index
* @param {number} credential_counter
* @param {number} attribute
* @returns {string}
*/
export function getAttributeCommitmentRandomness(seed_as_hex: string, raw_net: string, identity_provider_index: number, identity_index: number, credential_counter: number, attribute: number): string;
/**
* @param {string} seed_as_hex
* @param {string} raw_net
* @param {bigint} issuer_index
* @param {bigint} issuer_subindex
* @param {number} verifiable_credential_index
* @returns {string}
*/
export function getVerifiableCredentialSigningKey(seed_as_hex: string, raw_net: string, issuer_index: bigint, issuer_subindex: bigint, verifiable_credential_index: number): string;
/**
* @param {string} seed_as_hex
* @param {string} raw_net
* @param {bigint} issuer_index
* @param {bigint} issuer_subindex
* @param {number} verifiable_credential_index
* @returns {string}
*/
export function getVerifiableCredentialPublicKey(seed_as_hex: string, raw_net: string, issuer_index: bigint, issuer_subindex: bigint, verifiable_credential_index: number): string;
/**
* @param {string} seed_as_hex
* @param {string} raw_net
* @returns {string}
*/
export function getVerifiableCredentialBackupEncryptionKey(seed_as_hex: string, raw_net: string): string;
/**
* @param {any} signatures
* @param {string} unsigned_info
* @returns {Uint8Array}
*/
export function serializeCredentialDeploymentPayload(signatures: any, unsigned_info: string): Uint8Array;
/**
* @param {string} sender
* @returns {string}
*/
export function generateBakerKeys(sender: string): string;
/**
* @param {string} raw_input
* @returns {string}
*/
export function createWeb3IdProof(raw_input: string): string;
/**
* @param {string} raw_input
* @returns {boolean}
*/
export function verifyWeb3IdCredentialSignature(raw_input: string): boolean;
/**
* @param {string} input
* @returns {string}
*/
export function verifyPresentation(input: string): string;
/**
* Returns the Subdivision with the given code, if exists.
* #Sample
* ```
* let sub = rust_iso3166::iso3166_2::from_code("SE-O");
* assert_eq!("Västra Götalands län", sub.unwrap().name);
* ```
* @param {string} code
* @returns {Subdivision | undefined}
*/
export function from_code_iso_3166_2(code: string): Subdivision | undefined;
/**
* Returns the CountryCode with the given Alpha2 code, if exists.
* #Sample
* ```
* let country = rust_iso3166::from_alpha2("AU");
* assert_eq!("AUS", country.unwrap().alpha3);
* ```
* @param {string} alpha2
* @returns {CountryCode | undefined}
*/
export function from_alpha2(alpha2: string): CountryCode | undefined;
/**
* Returns the CountryCode with the given Alpha3 code, if exists.
* #Sample
* ```
* let country = rust_iso3166::from_alpha3("AUS");
* assert_eq!(036, country.unwrap().numeric);
* ```
* @param {string} alpha3
* @returns {CountryCode | undefined}
*/
export function from_alpha3(alpha3: string): CountryCode | undefined;
/**
* Returns the CountryCode with the given numeric , if exists.
* ```
* let country = rust_iso3166::from_numeric(036);
* assert_eq!("AUS", country.unwrap().alpha3);
* ```
* @param {number} numeric
* @returns {CountryCode | undefined}
*/
export function from_numeric(numeric: number): CountryCode | undefined;
/**
* Returns the CountryCode with the given numeric 3 length str, if exists.
* ```
* let country = rust_iso3166::from_numeric_str("036");
* assert_eq!("AUS", country.unwrap().alpha3);
* ```
* @param {string} numeric
* @returns {CountryCode | undefined}
*/
export function from_numeric_str(numeric: string): CountryCode | undefined;
/**
* Returns the CountryCode3 with the given Alpha4 code, if exists.
* #Sample
* ```
* let sub = rust_iso3166::iso3166_3::from_code("PZPA");
* assert_eq!("Panama Canal Zone", sub.unwrap().name);
* ```
* @param {string} alpha4
* @returns {CountryCode3 | undefined}
*/
export function from_code_iso_3166_3(alpha4: string): CountryCode3 | undefined;
/**
* # Sample code
* ```
* let country = rust_iso3166::from_alpha2("AU");
* assert_eq!("AUS", country.unwrap().alpha3); 
* let country = rust_iso3166::from_alpha3("AUS");
* assert_eq!("AU", country.unwrap().alpha2);  
* let country = rust_iso3166::from_numeric(036);
* assert_eq!("AUS", country.unwrap().alpha3);   
* let country = rust_iso3166::from_numeric_str("036");
* assert_eq!("AUS", country.unwrap().alpha3); 
* 
* println!("{:?}", country);   
* println!("{:?}", rust_iso3166::ALL);
* println!("{:?}", rust_iso3166::ALL_ALPHA2);   
* println!("{:?}", rust_iso3166::ALL_ALPHA3);   
* println!("{:?}", rust_iso3166::ALL_NAME);   
* println!("{:?}", rust_iso3166::ALL_NUMERIC);   
* println!("{:?}", rust_iso3166::ALL_NUMERIC_STR);   
* println!("{:?}", rust_iso3166::NUMERIC_MAP);  
* println!("{:?}", rust_iso3166::ALPHA3_MAP);  
* println!("{:?}", rust_iso3166::ALPHA2_MAP);  
* ```
* Data for each Country Code defined by ISO 3166-1
*/
export class CountryCode {
  free(): void;
/**
*Return len 3 String for CountryCode numeric
* @returns {string}
*/
  numeric_str(): string;
/**
* @returns {Array<any>}
*/
  subdivisions(): Array<any>;
/**
*/
  readonly alpha2: string;
/**
*/
  readonly alpha3: string;
/**
*/
  readonly name: string;
/**
*/
  readonly numeric: number;
}
/**
* Data for each Country Code defined by ISO 3166-1
*/
export class CountryCode3 {
  free(): void;
/**
*/
  readonly code: string;
/**
*/
  readonly desc: string;
/**
*/
  readonly former: CountryCode;
/**
*/
  readonly name: string;
/**
*/
  readonly new_countries: Array<any>;
}
/**
* # Sample code
* ```
* let country = rust_iso3166::from_alpha2("GB").unwrap();
* let subdivisions = country.subdivisions();
* assert!(subdivisions.unwrap().len() > 0);
* let country = rust_iso3166::iso3166_2::from_code("GB-EDH");
* assert_eq!("Edinburgh, City of", country.unwrap().name);
* println!("{:?}", rust_iso3166::iso3166_2::SUBDIVISION_COUNTRY_MAP); 
* println!("{:?}", rust_iso3166::iso3166_2::SUBDIVISION_MAP); 
* ```
* Data for each Country Code defined by ISO 3166-2
*/
export class Subdivision {
  free(): void;
/**
*/
  readonly code: string;
/**
*/
  readonly country_code: string;
/**
*/
  readonly country_name: string;
/**
*/
  readonly name: string;
/**
*/
  readonly region_code: string;
/**
*/
  readonly subdivision_type: string;
}
