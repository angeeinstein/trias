"""TRIAS API Client - handles all communication with the TRIAS public transit API"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Any
from config import TRIAS_API_URL, DEFAULT_REQUESTOR_REF, NAMESPACES


class TriasClient:
    """Client for interacting with the TRIAS API"""
    
    def __init__(self, requestor_ref: str = DEFAULT_REQUESTOR_REF):
        self.api_url = TRIAS_API_URL
        self.requestor_ref = requestor_ref
        self.namespaces = NAMESPACES
    
    def _get_timestamp(self) -> str:
        """Generate current UTC timestamp in ISO-8601 format with Z suffix"""
        return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    def _create_base_request(self) -> ET.Element:
        """Create the base XML structure for TRIAS requests"""
        trias = ET.Element('Trias', {
            'xmlns': self.namespaces['trias'],
            'xmlns:siri': self.namespaces['siri'],
            'version': '1.2'
        })
        
        service_request = ET.SubElement(trias, 'ServiceRequest')
        
        # Add timestamp
        timestamp = ET.SubElement(service_request, '{%s}RequestTimestamp' % self.namespaces['siri'])
        timestamp.text = self._get_timestamp()
        
        # Add requestor ref
        requestor_ref = ET.SubElement(service_request, '{%s}RequestorRef' % self.namespaces['siri'])
        requestor_ref.text = self.requestor_ref
        
        # Add request payload container
        request_payload = ET.SubElement(service_request, 'RequestPayload')
        
        return trias, request_payload
    
    def _make_request(self, xml_body: str) -> ET.Element:
        """Make HTTP POST request to TRIAS API"""
        headers = {
            'Content-Type': 'text/xml',
            'Accept': 'text/xml'
        }
        
        try:
            response = requests.post(
                self.api_url,
                data=xml_body.encode('utf-8'),
                headers=headers,
                timeout=30
            )
            
            # Log first part of response if error
            if response.status_code >= 400:
                print(f"HTTP {response.status_code}: {response.text[:2000]}")
                response.raise_for_status()
            
            # Parse XML response
            return ET.fromstring(response.content)
            
        except requests.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
    
    def search_location_by_name(
        self, 
        location_name: str, 
        number_of_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for stops/locations by name
        
        Args:
            location_name: Name of the location to search for
            number_of_results: Maximum number of results to return
            
        Returns:
            List of location dictionaries with stop_id, stop_name, coordinates, etc.
        """
        trias, request_payload = self._create_base_request()
        
        # Build LocationInformationRequest
        loc_info_req = ET.SubElement(request_payload, 'LocationInformationRequest')
        
        initial_input = ET.SubElement(loc_info_req, 'InitialInput')
        location_name_elem = ET.SubElement(initial_input, 'LocationName')
        text = ET.SubElement(location_name_elem, 'Text')
        text.text = location_name
        language = ET.SubElement(location_name_elem, 'Language')
        language.text = 'de'
        
        restrictions = ET.SubElement(loc_info_req, 'Restrictions')
        type_elem = ET.SubElement(restrictions, 'Type')
        type_elem.text = 'stop'
        num_results = ET.SubElement(restrictions, 'NumberOfResults')
        num_results.text = str(number_of_results)
        
        # Convert to string and make request
        xml_string = ET.tostring(trias, encoding='utf-8', method='xml')
        xml_declaration = b'<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_body = xml_declaration + xml_string
        
        response_root = self._make_request(xml_body.decode('utf-8'))
        
        # Parse response
        return self._parse_location_results(response_root)
    
    def search_location_by_coordinates(
        self,
        longitude: float,
        latitude: float,
        radius: int = 500,
        number_of_results: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Search for stops near coordinates within a radius
        
        Args:
            longitude: Longitude coordinate
            latitude: Latitude coordinate
            radius: Search radius in meters
            number_of_results: Maximum number of results
            
        Returns:
            List of location dictionaries
        """
        trias, request_payload = self._create_base_request()
        
        # Build LocationInformationRequest with GeoRestriction
        loc_info_req = ET.SubElement(request_payload, 'LocationInformationRequest')
        
        restrictions = ET.SubElement(loc_info_req, 'Restrictions')
        type_elem = ET.SubElement(restrictions, 'Type')
        type_elem.text = 'stop'
        num_results = ET.SubElement(restrictions, 'NumberOfResults')
        num_results.text = str(number_of_results)
        
        geo_restriction = ET.SubElement(loc_info_req, 'GeoRestriction')
        circle = ET.SubElement(geo_restriction, 'Circle')
        center = ET.SubElement(circle, 'Center')
        lon_elem = ET.SubElement(center, 'Longitude')
        lon_elem.text = str(longitude)
        lat_elem = ET.SubElement(center, 'Latitude')
        lat_elem.text = str(latitude)
        radius_elem = ET.SubElement(circle, 'Radius')
        radius_elem.text = str(radius)
        
        # Convert to string and make request
        xml_string = ET.tostring(trias, encoding='utf-8', method='xml')
        xml_declaration = b'<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_body = xml_declaration + xml_string
        
        response_root = self._make_request(xml_body.decode('utf-8'))
        
        # Parse response
        return self._parse_location_results(response_root)
    
    def get_departures(
        self,
        stop_id: str,
        number_of_results: int = 12,
        departure_window: int = 60,
        include_realtime: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get departure events for a stop
        
        Args:
            stop_id: StopPointRef ID (e.g., "at:46:7960")
            number_of_results: Maximum number of departures to return
            departure_window: Time window in minutes
            include_realtime: Whether to include realtime data
            
        Returns:
            List of departure dictionaries with times, line, destination, etc.
        """
        trias, request_payload = self._create_base_request()
        
        # Build StopEventRequest
        stop_event_req = ET.SubElement(request_payload, 'StopEventRequest')
        
        location = ET.SubElement(stop_event_req, 'Location')
        location_ref = ET.SubElement(location, 'LocationRef')
        stop_point_ref = ET.SubElement(location_ref, 'StopPointRef')
        stop_point_ref.text = stop_id
        
        params = ET.SubElement(stop_event_req, 'Params')
        num_results = ET.SubElement(params, 'NumberOfResults')
        num_results.text = str(number_of_results)
        stop_event_type = ET.SubElement(params, 'StopEventType')
        stop_event_type.text = 'departure'
        include_rt = ET.SubElement(params, 'IncludeRealtimeData')
        include_rt.text = 'true' if include_realtime else 'false'
        
        departure_window_elem = ET.SubElement(stop_event_req, 'DepartureWindow')
        departure_window_elem.text = str(departure_window)
        
        # Convert to string and make request
        xml_string = ET.tostring(trias, encoding='utf-8', method='xml')
        xml_declaration = b'<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_body = xml_declaration + xml_string
        
        response_root = self._make_request(xml_body.decode('utf-8'))
        
        # Parse response
        return self._parse_departure_results(response_root)
    
    def _parse_location_results(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Parse LocationInformationResponse"""
        results = []
        
        # Find all LocationResult elements
        for location_result in root.findall('.//trias:LocationResult', self.namespaces):
            try:
                # Get StopPointRef (unique stop ID)
                stop_point_ref = location_result.find('.//trias:StopPointRef', self.namespaces)
                if stop_point_ref is None:
                    continue
                
                # Get StopPointName (actual stop name)
                stop_point_name = location_result.find('.//trias:StopPointName/trias:Text', self.namespaces)
                
                # Get coordinates if available
                longitude_elem = location_result.find('.//trias:Longitude', self.namespaces)
                latitude_elem = location_result.find('.//trias:Latitude', self.namespaces)
                
                # Get locality name (city/area) if available
                locality_name = location_result.find('.//trias:LocalityName/trias:Text', self.namespaces)
                
                result = {
                    'stop_id': stop_point_ref.text,
                    'stop_name': stop_point_name.text if stop_point_name is not None else None,
                    'locality': locality_name.text if locality_name is not None else None,
                    'longitude': float(longitude_elem.text) if longitude_elem is not None else None,
                    'latitude': float(latitude_elem.text) if latitude_elem is not None else None
                }
                
                results.append(result)
                
            except Exception as e:
                print(f"Error parsing location result: {e}")
                continue
        
        # Deduplicate by stop_id
        seen = set()
        deduplicated = []
        for result in results:
            if result['stop_id'] not in seen:
                seen.add(result['stop_id'])
                deduplicated.append(result)
        
        return deduplicated
    
    def _parse_departure_results(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Parse StopEventResponse"""
        results = []
        
        # Find all StopEventResult elements
        for stop_event_result in root.findall('.//trias:StopEventResult', self.namespaces):
            try:
                stop_event = stop_event_result.find('trias:StopEvent', self.namespaces)
                if stop_event is None:
                    continue
                
                # Get times
                this_call = stop_event.find('.//trias:ThisCall', self.namespaces)
                call_at_stop = this_call.find('.//trias:CallAtStop', self.namespaces)
                service_departure = call_at_stop.find('.//trias:ServiceDeparture', self.namespaces)
                
                timetabled_time = service_departure.find('trias:TimetabledTime', self.namespaces)
                estimated_time = service_departure.find('trias:EstimatedTime', self.namespaces)
                
                # Get line info
                service = stop_event.find('.//trias:Service', self.namespaces)
                published_line = service.find('.//trias:PublishedLineName/trias:Text', self.namespaces)
                
                # Get destination
                destination = service.find('.//trias:DestinationText/trias:Text', self.namespaces)
                
                # Get mode (bus, tram, etc.)
                mode = service.find('.//trias:Mode/trias:PtMode', self.namespaces)
                
                # Calculate actual time and delay
                planned_time_str = timetabled_time.text if timetabled_time is not None else None
                estimated_time_str = estimated_time.text if estimated_time is not None else None
                actual_time_str = estimated_time_str if estimated_time_str else planned_time_str
                
                delay_minutes = None
                if planned_time_str and estimated_time_str:
                    try:
                        planned = datetime.fromisoformat(planned_time_str.replace('Z', '+00:00'))
                        estimated = datetime.fromisoformat(estimated_time_str.replace('Z', '+00:00'))
                        delay_seconds = (estimated - planned).total_seconds()
                        delay_minutes = round(delay_seconds / 60)
                    except:
                        pass
                
                result = {
                    'line': published_line.text if published_line is not None else None,
                    'destination': destination.text if destination is not None else None,
                    'mode': mode.text if mode is not None else None,
                    'planned_time': planned_time_str,
                    'estimated_time': estimated_time_str,
                    'actual_time': actual_time_str,
                    'delay_minutes': delay_minutes,
                    'has_realtime': estimated_time_str is not None
                }
                
                results.append(result)
                
            except Exception as e:
                print(f"Error parsing departure result: {e}")
                continue
        
        return results
